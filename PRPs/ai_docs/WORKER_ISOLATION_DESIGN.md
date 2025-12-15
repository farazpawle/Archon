# Worker Isolation Strategy Design

## 1. Strategy Comparison

### Option A: Celery / RQ
*   **Pros**: Mature ecosystem, built-in retries, monitoring (Flower), result backends.
*   **Cons**: Adds significant complexity (Redis/RabbitMQ dependency), "heavy" for a simple crawling workload, might conflict with our Postgres-based queue design (Task 1).
*   **Verdict**: Overkill. We already designed a custom Postgres queue to avoid adding Redis.

### Option B: Python `multiprocessing` Pool
*   **Pros**: Built-in, no extra deps.
*   **Cons**: Hard to manage worker lifecycle (restarts, memory leaks) over long periods. If the main process dies, children might zombie.
*   **Verdict**: Good for the *internal* execution of a job, but not for the top-level worker management.

### Option C: Containerized Workers (Docker) + Subprocess Execution
*   **Pros**: Best isolation. Each worker node is a container. Inside the container, we run a "Supervisor" script that polls jobs and spawns a fresh subprocess for each crawl.
*   **Cons**: Requires Docker infrastructure (which we have).
*   **Verdict**: **Selected Strategy**. This offers the best balance of isolation and simplicity.

## 2. Selected Design: The "Supervisor-Subprocess" Pattern

### Architecture
1.  **Supervisor Process (`worker.py`)**:
    *   Runs as the entry point of the Docker container.
    *   Responsible for **Polling** the `crawl_jobs` table (from Task 1).
    *   Responsible for **Heartbeats**.
    *   Responsible for **Spawning** the actual crawl process.
2.  **Execution Process (Subprocess)**:
    *   Spawned by Supervisor for a *single* job.
    *   Loads the `CrawlerManager` and runs the crawl.
    *   Exits when done (releasing all memory).
    *   If it crashes (Segfault/OOM), the Supervisor catches the non-zero exit code and updates the job status to 'failed'.

### Why this is better?
*   **Memory Leaks**: Crawlers (especially headless browsers) are notorious for leaking memory. By killing the process after every job, we guarantee a clean slate.
*   **Crash Isolation**: If a specific URL causes a segfault in the underlying browser engine, it only kills the subprocess. The Supervisor remains alive to report the error and pick up the next job.

## 3. Implementation Plan

### A. `worker_entrypoint.py` (Supervisor)
```python
import time
import subprocess
import sys
from db import get_next_job, update_job_status, send_heartbeat

def main():
    worker_id = uuid.uuid4()
    print(f"Worker {worker_id} started")
    
    while True:
        # 1. Poll for job
        job = get_next_job(worker_id)
        
        if not job:
            time.sleep(1)
            continue
            
        # 2. Spawn Subprocess
        print(f"Starting job {job['id']}")
        try:
            # Run the crawl script as a separate process
            # Pass job_id as argument
            result = subprocess.run(
                [sys.executable, "-m", "src.workers.crawl_runner", str(job['id'])],
                capture_output=True,
                text=True,
                timeout=3600 # 1 hour hard timeout
            )
            
            if result.returncode == 0:
                print(f"Job {job['id']} completed successfully")
                # Status update handled by runner, or double-checked here
            else:
                print(f"Job {job['id']} failed with code {result.returncode}")
                update_job_status(job['id'], 'failed', error=result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"Job {job['id']} timed out")
            update_job_status(job['id'], 'failed', error="Hard timeout exceeded")
            
        # 3. Heartbeat is handled by a separate thread in the supervisor
```

### B. `src/workers/crawl_runner.py` (The Runner)
```python
import sys
import asyncio
from services.crawling import CrawlingService

async def run_crawl(job_id):
    # 1. Fetch job details from DB
    job = await db.get_job(job_id)
    
    # 2. Initialize Crawler (fresh instance)
    async with CrawlerManager() as crawler:
        service = CrawlingService(crawler)
        
        # 3. Run Crawl
        # The service updates progress to DB directly
        await service.execute_job(job['payload'])
        
        # 4. Mark Complete
        await db.mark_job_complete(job_id)

if __name__ == "__main__":
    job_id = sys.argv[1]
    asyncio.run(run_crawl(job_id))
```

## 4. Progress Reporting
*   The `crawl_runner.py` process will instantiate the `CrawlingService`.
*   We need to modify `CrawlingService` (or `ProgressTracker`) to write to the `crawl_jobs` table (or a related `job_progress` table) instead of just the in-memory dict.
*   Since the Runner is a separate process, it has its own DB connection. This is fine.

## 5. Resource Limits
*   The Supervisor can enforce limits on the subprocess (e.g., `resource` module in Python to limit RAM).
*   Docker limits (CPU/RAM) apply to the whole container (Supervisor + Subprocess).
