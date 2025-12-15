import asyncio
import sys
import json
import traceback
from datetime import datetime, timezone
from src.server.utils import get_supabase_client
from src.server.config.logfire_config import get_logger
from src.server.services.crawler_manager import CrawlerManager
from src.server.services.crawling import CrawlingService

logger = get_logger(__name__)

async def run_job(job_id):
    supabase = get_supabase_client()
    
    try:
        # 1. Fetch job details
        response = supabase.table("crawl_jobs").select("*").eq("id", job_id).single().execute()
        if not response.data:
            logger.error(f"Job {job_id} not found")
            sys.exit(1)
            
        job = response.data
        payload = job["payload"]
        
        logger.info(f"Runner started for job {job_id} with payload: {payload}")
        
        # 2. Initialize Crawler
        crawler_manager = CrawlerManager()
        await crawler_manager.initialize()
        crawler = await crawler_manager.get_crawler()
        
        if not crawler:
            raise Exception("Failed to initialize crawler")
            
        # 3. Initialize Service
        service = CrawlingService(crawler, supabase)
        service.set_progress_id(job_id) # Use job_id as progress_id
        
        # 4. Execute
        # We need to adapt CrawlingService to support the job payload directly
        # For now, we map the payload to the request dict expected by orchestrate_crawl
        # But orchestrate_crawl spawns a task. We want to await it directly.
        # So we might need to call a lower-level method or modify orchestrate_crawl.
        
        # Let's assume we modify CrawlingService to have an execute_job method
        # or we use the existing logic but await the result.
        
        # The payload matches the request dict structure
        await service.execute_crawl_job(payload, job_id)
        
        # 5. Mark Complete
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("crawl_jobs").update({
            "status": "completed",
            "completed_at": now,
            "progress_percentage": 100
        }).eq("id", job_id).execute()
        
        logger.info(f"Job {job_id} finished successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        traceback.print_exc()
        
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("crawl_jobs").update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": now
        }).eq("id", job_id).execute()
        
        sys.exit(1)
    finally:
        await crawler_manager.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.workers.runner <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    asyncio.run(run_job(job_id))
