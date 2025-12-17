import asyncio
import os
import uuid
from datetime import UTC, datetime

from src.server.utils import get_supabase_client


async def debug_worker():
    print("--- Archon Worker Debugger ---")

    # 1. Check Environment
    print("Checking environment...")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url:
        print("❌ SUPABASE_URL is missing")
        return
    if not key:
        print("❌ SUPABASE_SERVICE_KEY is missing")
        return
    print("✅ Environment variables present")

    # 2. Connect to Supabase
    print(f"Connecting to Supabase at {url}...")
    try:
        supabase = get_supabase_client()
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        return

    # 3. Check for Pending Jobs
    print("Checking for ALL jobs...")
    try:
        response = supabase.table("crawl_jobs") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()

        jobs = response.data
        print(f"Found {len(jobs)} total jobs (showing last 10)")

        for job in jobs:
            print(f"  - Job ID: {job['id']}")
            print(f"    Status: {job['status']}")
            print(f"    URL: {job['payload'].get('url')}")
            print(f"    Created At: {job['created_at']}")
            print(f"    Worker ID: {job.get('worker_id')}")
            print(f"    Error Message: {job.get('error_message')}")
            print(f"    Completed At: {job.get('completed_at')}")

            # Check crawl state
            try:
                state_response = supabase.table("crawl_states").select("*").eq("job_id", job['id']).execute()
                if state_response.data:
                    state = state_response.data[0]
                    visited = len(state.get("visited_urls", []))
                    pending = len(state.get("pending_urls", []))
                    print(f"    Crawl State: Visited={visited}, Pending={pending}")
                else:
                    print("    Crawl State: Not found")

                    # Try to create one to test permissions/schema
                    if job == jobs[0]: # Only for the first one
                        print("    Attempting to create dummy crawl state...")
                        try:
                            dummy_res = supabase.table("crawl_states").insert({
                                "job_id": job['id'],
                                "visited_urls": ["http://test.com"],
                                "updated_at": datetime.now(UTC).isoformat()
                            }).execute()
                            print("    ✅ Dummy state created successfully")
                        except Exception as e:
                            print(f"    ❌ Failed to create dummy state: {e}")

            except Exception as e:
                print(f"    Crawl State Error: {e}")

    except Exception as e:
        print(f"❌ Failed to query pending jobs: {e}")
        return

    # 4. Check Crawled Pages
    print("\nChecking for crawled pages (last 5)...")
    try:
        pages_response = supabase.table("archon_crawled_pages") \
            .select("id, url, created_at, source_id") \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute()

        if pages_response.data:
            for page in pages_response.data:
                print(f"  - Page: {page['url']}")
                print(f"    Created At: {page['created_at']}")
                print(f"    Source ID: {page['source_id']}")
        else:
            print("  No pages found.")
    except Exception as e:
        print(f"❌ Failed to query crawled pages: {e}")

    # 5. Simulate Claiming (Dry Run)
    if jobs:
        job = jobs[0]
        job_id = job['id']
        print(f"\nAttempting to claim Job {job_id} (Dry Run)...")

        worker_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        print(f"  Worker ID: {worker_id}")
        print(f"  Time: {now}")

        # We won't actually update to avoid interfering with real worker if it wakes up
        # But we can check if we have permission to read the record specifically
        try:
            check = supabase.table("crawl_jobs").select("id").eq("id", job_id).single().execute()
            if check.data:
                print("✅ Successfully read specific job record")
            else:
                print("❌ Failed to read specific job record (not found)")
        except Exception as e:
            print(f"❌ Failed to read specific job record: {e}")

    print("\n--- Debug Complete ---")

if __name__ == "__main__":
    asyncio.run(debug_worker())
