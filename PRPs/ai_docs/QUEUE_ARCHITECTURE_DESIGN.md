# Queue-Based Crawling Architecture Design

## Overview
This document outlines the design for a persistent, queue-based architecture to decouple the Archon API from the crawling workers. This replaces the current in-memory `active_crawl_tasks` system, enabling horizontal scaling, priority scheduling, and crash recovery.

## 1. Database Schema

### Table: `crawl_jobs`
Stores the state of each crawling request.

```sql
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'paused');

CREATE TABLE crawl_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Job Configuration
    payload JSONB NOT NULL,             -- Contains url, depth, strategies, etc.
    priority INTEGER DEFAULT 0,         -- Higher number = higher priority
    
    -- State Tracking
    status job_status DEFAULT 'pending',
    worker_id UUID,                     -- ID of the worker currently processing this job
    progress_percentage INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ,         -- Updated by worker every N seconds
    
    -- Error Handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    
    -- Metadata
    source_id TEXT,                     -- Link to the knowledge item/source
    user_id UUID                        -- Owner of the job
);

-- Indexes for efficient polling
CREATE INDEX idx_crawl_jobs_status_priority ON crawl_jobs (status, priority DESC, created_at ASC);
CREATE INDEX idx_crawl_jobs_worker_heartbeat ON crawl_jobs (worker_id, last_heartbeat);
```

## 2. System Components & Flow

### A. API Server (Producer)
The API server no longer spawns `asyncio` tasks directly.
1.  **Receive Request**: `POST /knowledge-items/crawl`
2.  **Validate**: Check API keys, quotas.
3.  **Enqueue**: Insert row into `crawl_jobs` with `status='pending'`.
4.  **Respond**: Return `job_id` (which serves as the `progress_id`).

### B. Worker Nodes (Consumers)
Separate Python processes (or containers) that run the crawling logic.
1.  **Poll**: Loop that queries for available jobs.
    ```sql
    UPDATE crawl_jobs
    SET status = 'processing',
        worker_id = :my_worker_id,
        started_at = NOW(),
        last_heartbeat = NOW()
    WHERE id = (
        SELECT id
        FROM crawl_jobs
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING *;
    ```
    *Note: `FOR UPDATE SKIP LOCKED` is crucial for concurrent workers to avoid race conditions.*
2.  **Execute**: Initialize `CrawlerManager` and run the crawl strategy.
3.  **Heartbeat**: Background task updates `last_heartbeat` every 30 seconds.
4.  **Update Progress**: Update `progress_percentage` in DB (replacing in-memory `ProgressTracker` or syncing with it).
5.  **Complete**: Update `status='completed'`, `completed_at=NOW()`.
6.  **Error**: Update `status='failed'`, `error_message=...`.

### C. Progress Tracking
The `ProgressTracker` currently uses in-memory dictionaries. This needs to be adapted:
*   **Option A (Hybrid)**: Workers write to DB `crawl_jobs`. API polls DB for `GET /crawl-progress/{id}`.
*   **Option B (Realtime)**: Workers publish events to Supabase Realtime channel. Frontend subscribes directly.
*   **Recommendation**: Option A is more robust for "status checks". Option B is better for live UI updates. We can implement A first.

## 3. Crash Recovery (The "Reaper")
A background process (can run on any worker or the API) monitors for stale jobs.
1.  **Scan**: Find jobs where `status='processing'` AND `last_heartbeat < NOW() - INTERVAL '2 minutes'`.
2.  **Recover**:
    *   If `retry_count < max_retries`: Set `status='pending'`, `worker_id=NULL`, increment `retry_count`.
    *   If `retry_count >= max_retries`: Set `status='failed'`, `error_message='Worker timed out'`.

## 4. Dispatch Mechanism
*   **Polling**: Simple, robust, works with standard Postgres. Recommended interval: 1-5 seconds.
*   **Notification**: Use `LISTEN/NOTIFY` or Supabase Realtime to wake up workers immediately when a job is inserted. This reduces latency but adds complexity.
*   **Decision**: Start with **Polling (1s)**. It's simple and sufficient for crawling workloads (which take minutes).

## 5. Migration Strategy
1.  Create `crawl_jobs` table.
2.  Create `WorkerService` class to handle the polling/execution loop.
3.  Update `KnowledgeAPI` to enqueue instead of spawn.
4.  Create a `worker_entrypoint.py` script.
