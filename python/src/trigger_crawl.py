import asyncio
import uuid

from src.server.utils import get_supabase_client


async def trigger_crawl():
    supabase = get_supabase_client()

    job_id = str(uuid.uuid4())
    url = "https://docs.python.org/3/library/asyncio.html"

    payload = {
        "url": url,
        "max_depth": 1,
        "max_concurrent": 1,
        "extract_code_examples": False
    }

    print(f"Creating job {job_id} for {url}")

    data = {
        "id": job_id,
        "status": "pending",
        "payload": payload
    }

    supabase.table("crawl_jobs").insert(data).execute()
    print("Job created.")

    # Monitor
    print("Monitoring job...")
    while True:
        response = supabase.table("crawl_jobs").select("*").eq("id", job_id).single().execute()
        job = response.data
        print(f"Status: {job['status']}, Progress: {job.get('progress_percentage')}%")

        # Check state
        state_response = supabase.table("crawl_states").select("*").eq("job_id", job_id).execute()
        if state_response.data:
            state = state_response.data[0]
            print(f"State found! Visited: {len(state.get('visited_urls', []))}")
        else:
            print("No state record yet.")

        if job['status'] in ['completed', 'failed']:
            break

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(trigger_crawl())
