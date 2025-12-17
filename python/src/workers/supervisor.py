import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

from src.server.config.logfire_config import get_logger
from src.server.utils import get_supabase_client

logger = get_logger(__name__)

class CrawlSupervisor:
    def __init__(self):
        self.worker_id = str(uuid.uuid4())
        self.supabase = get_supabase_client()
        self.running = True
        self.active_tasks = set()
        self.max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))

    async def start(self):
        logger.info(f"Worker Supervisor {self.worker_id} started with max {self.max_concurrent_jobs} concurrent jobs")

        # Start Watchdog
        asyncio.create_task(self.run_watchdog())

        while self.running:
            try:
                # Clean up finished tasks
                self.active_tasks = {t for t in self.active_tasks if not t.done()}

                if len(self.active_tasks) < self.max_concurrent_jobs:
                    job = await self.poll_job()
                    if job:
                        # Create background task
                        task = asyncio.create_task(self.process_job(job))
                        self.active_tasks.add(task)
                        # Continue immediately to try to pick up more jobs if available
                        continue
                    else:
                        await asyncio.sleep(1)
                else:
                    # Wait if we reached concurrency limit
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Supervisor loop error: {e}")
                await asyncio.sleep(5)

    async def run_watchdog(self):
        """Background task to recover stale jobs"""
        logger.info("Watchdog started")
        while self.running:
            try:
                # 1. Find stale jobs (processing but no heartbeat for > 2 mins)
                response = self.supabase.table("crawl_jobs") \
                    .select("id, last_heartbeat, retry_count, max_retries") \
                    .eq("status", "processing") \
                    .execute()

                if response.data:
                    now = datetime.now(UTC)
                    for job in response.data:
                        last_heartbeat_str = job.get("last_heartbeat")
                        if not last_heartbeat_str:
                            continue

                        # Parse ISO format
                        try:
                            last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace('Z', '+00:00'))
                        except ValueError:
                            # Handle cases where format might be different or already has offset
                            last_heartbeat = datetime.fromisoformat(last_heartbeat_str)

                        # Check if stale (> 2 mins)
                        if (now - last_heartbeat).total_seconds() > 120:
                            logger.warning(f"Watchdog found stale job {job['id']} (last heartbeat: {last_heartbeat})")
                            await self.recover_job(job)

            except Exception as e:
                logger.error(f"Watchdog error: {e}")

            await asyncio.sleep(60) # Run every minute

    async def recover_job(self, job):
        job_id = job["id"]
        retry_count = job.get("retry_count", 0)
        max_retries = job.get("max_retries", 3)

        if retry_count < max_retries:
            logger.info(f"Recovering job {job_id} (Retry {retry_count + 1}/{max_retries})")
            self.supabase.table("crawl_jobs").update({
                "status": "pending",
                "worker_id": None,
                "retry_count": retry_count + 1,
                "error_message": "Recovered from crash by Watchdog"
            }).eq("id", job_id).execute()
        else:
            logger.error(f"Job {job_id} exceeded max retries. Marking as failed.")
            self.supabase.table("crawl_jobs").update({
                "status": "failed",
                "error_message": "Job crashed and exceeded max retries"
            }).eq("id", job_id).execute()

    async def poll_job(self):
        # Simple optimistic locking strategy
        # 1. Find a pending job
        try:
            response = self.supabase.table("crawl_jobs") \
                .select("id") \
                .eq("status", "pending") \
                .order("priority", desc=True) \
                .order("created_at", desc=False) \
                .limit(1) \
                .execute()

            if not response.data:
                return None

            job_id = response.data[0]["id"]

            # 2. Try to claim it
            now = datetime.now(UTC).isoformat()
            update_response = self.supabase.table("crawl_jobs") \
                .update({
                    "status": "processing",
                    "worker_id": self.worker_id,
                    "started_at": now,
                    "last_heartbeat": now
                }) \
                .eq("id", job_id) \
                .eq("status", "pending") \
                .execute()

            if update_response.data:
                return update_response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error polling job: {e}")
            return None

    async def process_job(self, job):
        job_id = job["id"]
        logger.info(f"Starting job {job_id}")
        start_time = datetime.now()

        try:
            # Spawn subprocess
            # We use sys.executable to ensure we use the same python environment
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd() # Ensure src is in path

            logger.info(f"Spawning runner process for job {job_id}...")
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "src.workers.runner", job_id,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info(f"Runner process spawned for job {job_id} (PID: {process.pid})")

            # Monitor process and update heartbeat
            while True:
                try:
                    # Wait for process with timeout to send heartbeats
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                    break
                except TimeoutError:
                    # Update heartbeat
                    now = datetime.now(UTC).isoformat()
                    self.supabase.table("crawl_jobs") \
                        .update({"last_heartbeat": now}) \
                        .eq("id", job_id) \
                        .execute()

            stdout, stderr = await process.communicate()

            if stdout:
                logger.info(f"Job {job_id} stdout: {stdout.decode()}")
            if stderr:
                logger.warning(f"Job {job_id} stderr: {stderr.decode()}")

            if process.returncode == 0:
                logger.info(f"Job {job_id} completed successfully")
                # Status update should be handled by runner, but we double check
                # or mark as completed if runner didn't (though runner should)
            else:
                logger.error(f"Job {job_id} failed with code {process.returncode}")
                logger.error(f"Stderr: {stderr.decode()}")

                self.supabase.table("crawl_jobs") \
                    .update({
                        "status": "failed",
                        "error_message": f"Process failed with code {process.returncode}: {stderr.decode()[:1000]}"
                    }) \
                    .eq("id", job_id) \
                    .execute()

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            self.supabase.table("crawl_jobs") \
                .update({
                    "status": "failed",
                    "error_message": str(e)
                }) \
                .eq("id", job_id) \
                .execute()

if __name__ == "__main__":
    supervisor = CrawlSupervisor()
    asyncio.run(supervisor.start())
