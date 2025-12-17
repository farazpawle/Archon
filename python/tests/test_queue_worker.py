import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workers.runner import run_job
from src.workers.supervisor import CrawlSupervisor


@pytest.mark.asyncio
async def test_runner_execution():
    """Test that the runner executes a job correctly."""

    job_id = str(uuid.uuid4())
    payload = {
        "url": "https://example.com",
        "knowledge_type": "technical",
        "tags": ["test"],
        "max_depth": 1,
        "extract_code_examples": False,
        "generate_summary": True
    }

    # Mock Supabase client
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    # Mock CrawlerManager
    mock_crawler_manager = MagicMock()
    mock_crawler_manager.initialize = AsyncMock()
    mock_crawler_manager.get_crawler = AsyncMock(return_value=AsyncMock())
    mock_crawler_manager.cleanup = AsyncMock()

    # Mock CrawlingService
    mock_crawling_service = MagicMock()
    mock_crawling_service.execute_crawl_job = AsyncMock()

    with patch("src.workers.runner.get_supabase_client", return_value=mock_supabase), \
         patch("src.workers.runner.CrawlerManager", return_value=mock_crawler_manager), \
         patch("src.workers.runner.CrawlingService", return_value=mock_crawling_service):

        # Setup mock responses for fetching the job
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": job_id,
            "payload": payload,
            "status": "pending"
        }

        # Run the job
        await run_job(job_id)

        # Verify CrawlingService was initialized and execute_crawl_job was called
        mock_crawling_service.execute_crawl_job.assert_called_once()

        # Verify status updates
        # The runner only updates to completed (supervisor updates to processing)
        assert mock_table.update.call_count >= 1

        # Check calls to update
        calls = mock_table.update.call_args_list

        # Last update should be to 'completed'
        completed_call = calls[-1]
        assert completed_call[0][0]["status"] == "completed"

@pytest.mark.asyncio
async def test_supervisor_process_job():
    """Test that the supervisor processes a job correctly."""

    supervisor = CrawlSupervisor()

    # Mock Supabase
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    # Mock asyncio.create_subprocess_exec
    mock_process = AsyncMock()
    mock_process.wait = AsyncMock(return_value=None)
    mock_process.communicate = AsyncMock(return_value=(b"", b""))
    mock_process.returncode = 0

    with patch("src.workers.supervisor.get_supabase_client", return_value=mock_supabase), \
         patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:

        job_id = str(uuid.uuid4())
        job = {"id": job_id, "status": "pending"}

        # Test process_job
        await supervisor.process_job(job)

        assert mock_exec.call_count == 1
        args = mock_exec.call_args
        # args[0] are positional args: sys.executable, "-m", "src.workers.runner", job_id
        assert args[0][1] == "-m"
        assert args[0][2] == "src.workers.runner"
        assert args[0][3] == job_id

