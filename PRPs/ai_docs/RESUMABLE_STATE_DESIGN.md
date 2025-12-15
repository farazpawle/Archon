# Resumable Crawl State Design

## Overview
To enable true "stop and resume" functionality (persisting across server restarts or crashes), we need to store the internal state of the crawler in the database. This includes the "Frontier" (URLs waiting to be crawled) and the "Visited Set" (URLs already processed).

## 1. Database Schema

### Table: `crawl_states`
Stores the checkpoint data for a specific job.

```sql
CREATE TABLE crawl_states (
    job_id UUID PRIMARY KEY REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    
    -- The Frontier: List of URLs waiting to be processed
    -- Stored as JSONB: [{ "url": "...", "depth": 1, "parent": "..." }, ...]
    frontier JSONB DEFAULT '[]'::jsonb,
    
    -- The Visited Set: List of URL hashes or full URLs to prevent loops
    -- Stored as JSONB array of strings. For very large crawls, we might need a separate table.
    visited_urls JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    total_processed INTEGER DEFAULT 0,
    current_depth INTEGER DEFAULT 0,
    
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Scalability Note
For massive crawls (>10k pages), storing `visited_urls` in a single JSONB column is inefficient.
**Alternative for Scale**:
```sql
CREATE TABLE crawl_visited (
    job_id UUID REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    url_hash TEXT NOT NULL, -- MD5/SHA256 of URL
    PRIMARY KEY (job_id, url_hash)
);
```
*Decision*: Start with JSONB for simplicity (Archon seems targeted at documentation/small-medium sites). If `visited_urls` exceeds 10MB, we switch to the table approach.

## 2. Checkpointing Logic

The `BatchCrawlStrategy` (or `RecursiveCrawlStrategy`) needs to be modified to support a `checkpoint_callback`.

### Modified Strategy Logic (Pseudocode)
```python
class ResumableBatchStrategy:
    def __init__(self, job_id, db_client):
        self.job_id = job_id
        self.db = db_client
        self.frontier = []
        self.visited = set()
        
    async def load_state(self):
        """Load state from DB if exists"""
        state = await self.db.get_crawl_state(self.job_id)
        if state:
            self.frontier = state['frontier']
            self.visited = set(state['visited_urls'])
            
    async def save_checkpoint(self):
        """Save current state to DB"""
        await self.db.upsert_crawl_state(
            job_id=self.job_id,
            frontier=self.frontier,
            visited=list(self.visited)
        )

    async def crawl(self):
        # Load previous state if resuming
        await self.load_state()
        
        while self.frontier:
            batch = self.get_next_batch()
            
            # Process Batch
            results = await self.crawler.arun_many(batch)
            
            # Update State
            for res in results:
                self.visited.add(res.url)
                new_links = extract_links(res)
                self.add_to_frontier(new_links)
            
            # Checkpoint every N batches (e.g., every 50 pages)
            if self.should_checkpoint():
                await self.save_checkpoint()
```

## 3. Recovery Logic

When a worker starts a job, it checks if it's a "fresh" start or a "resume".

### Worker Logic
1.  **Fetch Job**: `SELECT * FROM crawl_jobs WHERE ...`
2.  **Check Status**:
    *   If `status` was 'pending' (fresh): Start from seed URL.
    *   If `status` was 'processing' (crash recovery) or 'paused' (user resume):
        *   Load state from `crawl_states`.
        *   If state exists: Initialize strategy with `frontier` and `visited`.
        *   If state missing: Fallback to seed URL (restart).

## 4. Integration with Pause/Resume
The current "Pause" feature uses an in-memory `asyncio.Event`.
With this design:
*   **Pause**: User clicks Pause -> API sets `status='paused'` -> Worker detects status change -> Saves Checkpoint -> Exits process.
*   **Resume**: User clicks Resume -> API sets `status='pending'` (or 'queued') -> Worker picks it up -> Loads Checkpoint -> Continues.

This unifies "Pause" and "Crash Recovery" into a single robust mechanism.
