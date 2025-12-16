-- Add total_pending column to crawl_states for efficient querying
ALTER TABLE crawl_states ADD COLUMN IF NOT EXISTS total_pending INTEGER DEFAULT 0;

-- Record this migration
INSERT INTO archon_migrations (version, migration_name)
VALUES ('0.1.0', '013_add_total_pending_column')
ON CONFLICT (version, migration_name) DO NOTHING;
