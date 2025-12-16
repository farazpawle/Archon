"""Progress API endpoints for polling operation status."""

from datetime import datetime
from email.utils import formatdate

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi import status as http_status

from ..config.logfire_config import get_logger, logfire
from ..models.progress_models import create_progress_response
from ..utils import get_supabase_client
from ..utils.etag_utils import check_etag, generate_etag
from ..utils.progress import ProgressTracker

logger = get_logger(__name__)

router = APIRouter(prefix="/api/progress", tags=["progress"])

# Terminal states that don't require further polling
TERMINAL_STATES = {"completed", "failed", "error", "cancelled"}


@router.get("/{operation_id}")
async def get_progress(
    operation_id: str,
    response: Response,
    if_none_match: str | None = Header(None)
):
    """
    Get progress for an operation with ETag support.

    Returns progress state with percentage, status, and message.
    Clients should poll this endpoint to track long-running operations.
    """
    try:
        logfire.info(f"Getting progress for operation | operation_id={operation_id}")

        # Get operation progress from ProgressTracker
        operation = ProgressTracker.get_progress(operation_id)

        # If in memory but not terminal, check DB for updates (for crawl type)
        # This ensures we catch updates from worker processes
        if operation and operation.get("type") == "crawl" and operation.get("status") not in TERMINAL_STATES:
            try:
                supabase = get_supabase_client()
                response = supabase.table("crawl_jobs").select("status, error_message").eq("id", operation_id).execute()
                if response.data:
                    job = response.data[0]
                    db_status = job["status"]
                    if db_status != operation.get("status"):
                        logfire.info(f"Syncing single progress from DB | id={operation_id} | memory={operation.get('status')} | db={db_status}")
                        operation["status"] = db_status
                        if db_status == "completed":
                            operation["progress"] = 100
                            operation["log"] = "Completed (synced from DB)"
                        elif db_status == "failed":
                            operation["error"] = job.get("error_message")
                            operation["log"] = f"Failed: {job.get('error_message')}"
                    
                    # If still processing or paused, fetch progress from crawl_states to reflect worker progress
                    if db_status in ["processing", "paused"]:
                        state_response = supabase.table("crawl_states").select("visited_urls, frontier, total_pending").eq("job_id", operation_id).execute()
                        if state_response.data:
                            state = state_response.data[0]
                            visited = len(state.get("visited_urls", []) or [])
                            # Use total_pending if available
                            pending = state.get("total_pending")
                            if pending is None:
                                pending = len(state.get("frontier", []) or [])
                                
                            total = visited + pending
                            if total > 0:
                                new_progress = int((visited / total) * 100)
                                # Only update if progress has advanced or is different
                                if new_progress != operation.get("progress", 0):
                                    operation["progress"] = new_progress
                                    if db_status == "paused":
                                        operation["log"] = f"Paused at {visited}/{total} pages..."
                                    else:
                                        operation["log"] = f"Processed {visited}/{total} pages..."
                                    logfire.debug(f"Synced progress from DB | id={operation_id} | progress={new_progress}%")
                            else:
                                # Initialized but no pages found yet (startup phase)
                                operation["progress"] = 0
                                operation["log"] = "Worker starting..."
            except Exception as e:
                logfire.error(f"Failed to sync single progress with DB: {e}")

        if not operation:
            logfire.warning(f"Operation not found | operation_id={operation_id}")
            raise HTTPException(
                status_code=404,
                detail={"error": f"Operation {operation_id} not found"}
            )


        # Ensure we have the progress_id in the response without mutating shared state
        operation_with_id = {**operation, "progress_id": operation_id}

        # Get operation type for proper model selection
        operation_type = operation.get("type", "crawl")

        # Create standardized response using Pydantic model
        progress_response = create_progress_response(operation_type, operation_with_id)


        # Convert to dict with camelCase fields for API response
        response_data = progress_response.model_dump(by_alias=True, exclude_none=True)

        # Debug logging for code extraction fields
        if operation_type == "crawl" and operation.get("status") == "code_extraction":
            logger.info(f"Code extraction response fields: completedSummaries={response_data.get('completedSummaries')}, totalSummaries={response_data.get('totalSummaries')}, codeBlocksFound={response_data.get('codeBlocksFound')}")

        # Generate ETag from stable data (excluding timestamp)
        etag_data = {k: v for k, v in response_data.items() if k != "timestamp"}
        current_etag = generate_etag(etag_data)

        # Check if client's ETag matches
        if check_etag(if_none_match, current_etag):
            return Response(
                status_code=http_status.HTTP_304_NOT_MODIFIED,
                headers={"ETag": current_etag, "Cache-Control": "no-cache, must-revalidate"},
            )

        # Set headers for caching
        response.headers["ETag"] = current_etag
        response.headers["Last-Modified"] = formatdate(timeval=None, localtime=False, usegmt=True)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"

        # Add polling hint headers
        if operation.get("status") not in TERMINAL_STATES:
            # Suggest polling every second for active operations
            response.headers["X-Poll-Interval"] = "1000"
        else:
            # No need to poll terminal operations
            response.headers["X-Poll-Interval"] = "0"

        logfire.info(f"Progress retrieved | operation_id={operation_id} | status={response_data.get('status')} | progress={response_data.get('progress')}")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(f"Failed to get progress | error={e!s} | operation_id={operation_id}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)}) from e


@router.get("/")
async def list_active_operations():
    """
    List all active operations.

    This endpoint is useful for debugging and monitoring active operations.
    """
    try:
        logfire.info("Listing active operations")

        # Sync with DB for crawl operations to ensure we have latest status from workers
        crawl_ids = [
            op_id for op_id, op in ProgressTracker.list_active().items() 
            if op.get("type") == "crawl" and op.get("status") not in TERMINAL_STATES
        ]
        
        if crawl_ids:
            try:
                supabase = get_supabase_client()
                # Batch query to check status of all active crawls
                response = supabase.table("crawl_jobs").select("id, status, error_message").in_("id", crawl_ids).execute()
                
                if response.data:
                    for job in response.data:
                        job_id = job["id"]
                        db_status = job["status"]
                        
                        # Get current memory state
                        op = ProgressTracker.get_progress(job_id)
                        if op and op.get("status") != db_status:
                            logfire.info(f"Syncing progress from DB | id={job_id} | memory={op.get('status')} | db={db_status}")
                            
                            # Update status in memory
                            op["status"] = db_status
                            
                            # Update other fields based on status
                            if db_status == "completed":
                                op["progress"] = 100
                                op["log"] = "Completed (synced from DB)"
                            elif db_status == "failed":
                                op["error"] = job.get("error_message")
                                op["log"] = f"Failed: {job.get('error_message')}"
            except Exception as e:
                # Don't fail the whole request if DB sync fails, just log it
                logfire.error(f"Failed to sync with DB active operations: {e}")

        # Get all active operations from ProgressTracker
        active_operations = []
        tracker_active = ProgressTracker.list_active()

        # Get active operations from ProgressTracker
        # Include all non-completed statuses
        for op_id, operation in tracker_active.items():
            status = operation.get("status", "unknown")
            # Include all operations that aren't in terminal states
            if status not in TERMINAL_STATES:
                operation_data = {
                    "operation_id": op_id,
                    "operation_type": operation.get("type", "unknown"),
                    "status": operation.get("status"),
                    "progress": operation.get("progress", 0),
                    "message": operation.get("log", "Processing..."),
                    "started_at": operation.get("start_time") or datetime.utcnow().isoformat(),
                    # Include source_id if available (for refresh operations)
                    "source_id": operation.get("source_id"),
                    # Include URL information for matching
                    "url": operation.get("url"),
                    "current_url": operation.get("current_url"),
                    # Include crawl type
                    "crawl_type": operation.get("crawl_type"),
                    # Include stats if available
                    "pages_crawled": operation.get("pages_crawled") or operation.get("processed_pages"),
                    "total_pages": operation.get("total_pages"),
                    "documents_created": operation.get("documents_created") or operation.get("chunks_stored"),
                    "code_blocks_found": operation.get("code_blocks_found") or operation.get("code_examples_found"),
                }
                # Only include non-None values to keep response clean
                active_operations.append({k: v for k, v in operation_data.items() if v is not None})

        # Fetch active jobs from DB that are NOT in tracker (e.g. from worker or after restart)
        try:
            supabase = get_supabase_client()
            # Fetch pending, processing, and PAUSED jobs
            db_jobs = supabase.table("crawl_jobs").select("*").in_("status", ["pending", "processing", "paused"]).execute()
            
            if db_jobs.data:
                # Optimization: Batch fetch states for processing/paused jobs to calculate progress
                active_ids = [j['id'] for j in db_jobs.data if j['status'] in ['processing', 'paused']]
                job_states = {}
                if active_ids:
                    try:
                        states_response = supabase.table("crawl_states").select("job_id, visited_urls, frontier, total_pending").in_("job_id", active_ids).execute()
                        if states_response.data:
                            for state in states_response.data:
                                job_states[state['job_id']] = state
                    except Exception as e:
                        logfire.error(f"Failed to fetch crawl states: {e}")

                for job in db_jobs.data:
                    job_id = job["id"]
                    
                    # Skip if already in tracker (handled above)
                    if job_id in tracker_active:
                        continue
                        
                    # Create synthetic operation for DB job
                    payload = job.get("payload") or {}
                    status = job["status"]
                    
                    # Basic progress estimation for DB-only jobs
                    progress = 0
                    message = "Waiting for worker..."
                    
                    if status in ["processing", "paused"]:
                        # Try to get accurate progress from pre-fetched crawl_states
                        state = job_states.get(job_id)
                        if state:
                            visited = len(state.get("visited_urls", []) or [])
                            # Use total_pending if available (new schema), else fallback to frontier length
                            pending = state.get("total_pending")
                            if pending is None:
                                pending = len(state.get("frontier", []) or [])
                                
                            total = visited + pending
                            if total > 0:
                                progress = int((visited / total) * 100)
                                if status == "paused":
                                    message = f"Paused at {visited}/{total} pages..."
                                else:
                                    message = f"Processed {visited}/{total} pages..."
                            else:
                                progress = 0
                                message = "Worker starting..."
                        else:
                            progress = 0  # Fallback if no state found
                            message = "Worker starting..."
                    
                    op_data = {
                        "operation_id": job_id,
                        "operation_type": "crawl",
                        "status": status,
                        "progress": progress,
                        "message": message,
                        "started_at": job["created_at"],
                        "url": payload.get("url"),
                        "crawl_type": payload.get("knowledge_type", "general"),
                        "source_id": None, # Can't easily get this without joining
                    }
                    active_operations.append({k: v for k, v in op_data.items() if v is not None})
                    
        except Exception as e:
            logfire.error(f"Failed to fetch active DB jobs: {e}")

        logfire.info(f"Active operations listed | count={len(active_operations)}")

        return {
            "operations": active_operations,
            "count": len(active_operations),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logfire.error(f"Failed to list active operations | error={e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)}) from e
