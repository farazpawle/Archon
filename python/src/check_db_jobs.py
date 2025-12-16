
import asyncio
import os
import sys

# Inside container, /app is usually the root, and /app/src is where code is.
# If we run from /app, 'src' is a package.
# If we run from /app/src, we might need to adjust.

from src.server.utils import get_supabase_client

async def check_jobs():
    # Env vars are already loaded in the container
    supabase = get_supabase_client()
    
    print("--- Checking crawl_jobs ---")
    response = supabase.table("crawl_jobs").select("*").in_("status", ["pending", "processing"]).execute()
    jobs = response.data
    print(f"Found {len(jobs)} active jobs:")
    for job in jobs:
        print(f"ID: {job['id']} | Status: {job['status']} | Created: {job['created_at']} | URL: {job['payload'].get('url')}")

    print("\n--- Checking crawl_states ---")
    if jobs:
        job_ids = [j['id'] for j in jobs]
        response = supabase.table("crawl_states").select("*").in_("job_id", job_ids).execute()
        states = response.data
        for state in states:
            visited = len(state.get("visited_urls", []) or [])
            # Use total_pending if available, otherwise calculate from frontier
            pending = state.get("total_pending")
            if pending is None:
                pending = len(state.get("frontier", []) or [])
            
            print(f"Job {state['job_id']} State: Visited={visited}, Pending={pending}, Total={visited+pending}")

if __name__ == "__main__":
    asyncio.run(check_jobs())
