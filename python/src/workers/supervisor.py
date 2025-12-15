import asyncio
import uuid
import subprocess
import sys
import os
import json
from datetime import datetime, timezone
from src.server.utils import get_supabase_client
from src.server.config.logfire_config import get_logger

logger = get_logger(__name__)

class CrawlSupervisor:
    def __init__(self):
        self.worker_id = str(uuid.uuid4())
        self.supabase = get_supabase_client()
        self.running = True

    async def start(self):
        logger.info(f"Worker Supervisor {self.worker_id} started")
        while self.running:
            try:
                job = await self.poll_job()
                if job:
                    await self.process_job(job)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Supervisor loop error: {e}")
                await asyncio.sleep(5)

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
            now = datetime.now(timezone.utc).isoformat()
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
        
        try:
            # Spawn subprocess
            # We use sys.executable to ensure we use the same python environment
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd() # Ensure src is in path
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "src.workers.runner", job_id,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor process and update heartbeat
            while True:
                try:
                    # Wait for process with timeout to send heartbeats
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                    break
                except asyncio.TimeoutError:
                    # Update heartbeat
                    now = datetime.now(timezone.utc).isoformat()
                    self.supabase.table("crawl_jobs") \
                        .update({"last_heartbeat": now}) \
                        .eq("id", job_id) \
                        .execute()
            
            stdout, stderr = await process.communicate()
            
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
