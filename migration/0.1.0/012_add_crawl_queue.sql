-- Create job_status enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'paused');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create crawl_jobs table
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payload JSONB NOT NULL,
    priority INTEGER DEFAULT 0,
    status job_status DEFAULT 'pending',
    worker_id UUID,
    progress_percentage INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    source_id TEXT,
    user_id UUID
);

-- Create indexes for crawl_jobs
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status_priority ON crawl_jobs (status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_worker_heartbeat ON crawl_jobs (worker_id, last_heartbeat);

-- Create crawl_states table
CREATE TABLE IF NOT EXISTS crawl_states (
    job_id UUID PRIMARY KEY REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    frontier JSONB DEFAULT '[]'::jsonb,
    visited_urls JSONB DEFAULT '[]'::jsonb,
    total_processed INTEGER DEFAULT 0,
    current_depth INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
