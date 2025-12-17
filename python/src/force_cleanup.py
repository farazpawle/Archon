
import asyncio
from datetime import UTC, datetime

from src.server.utils import get_supabase_client


async def cleanup():
    supabase = get_supabase_client()
    print("Cancelling all pending/processing jobs...")

    # Get IDs first to log them
    jobs = supabase.table("crawl_jobs").select("id").in_("status", ["pending", "processing"]).execute()
    ids = [j['id'] for j in jobs.data]
    print(f"Found jobs to cancel: {ids}")

    if ids:
        response = supabase.table("crawl_jobs").update({
            "status": "failed",
            "error_message": "Force cancelled by system cleanup",
            "completed_at": datetime.now(UTC).isoformat()
        }).in_("id", ids).execute()
        print(f"Cancelled {len(response.data)} jobs.")
    else:
        print("No active jobs found.")

if __name__ == "__main__":
    asyncio.run(cleanup())
