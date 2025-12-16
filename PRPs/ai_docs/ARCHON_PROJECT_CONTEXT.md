# Archon Project Context

## 1. Project Identity

**Name:** Archon  
**Description:** A "command center" for AI coding assistants (Claude Code, Cursor, Windsurf). It acts as a Model Context Protocol (MCP) server to provide AI agents with curated knowledge, context, and task management capabilities.  
**Core Value:** Enables AI agents to access your documentation (crawled or uploaded), manage tasks, and maintain project context, replacing the need for manual context pasting.  
**Status:** Beta (Local-only deployment, fix-forward approach, detailed errors over graceful failures).  
**Latest Updates (Dec 16, 2025):** Implemented fault-tolerant job tracking with Supervisor-Worker architecture, pause/resume functionality with DB-driven state sync, and enhanced UI status visualization for paused operations.

---

## 2. Tech Stack

### Frontend (`archon-ui-main/`)

| Technology | Version | Purpose |
| --- | --- | --- |
| React | 18 | UI Framework |
| TypeScript | 5 | Type Safety |
| Vite | 5.2 | Build Tool & Dev Server |
| Tailwind CSS | 4.1 | Styling (Glassmorphism) |
| TanStack Query | 5.85 | Server State Management |
| Radix UI | Latest | Accessible Component Primitives |
| React Router | 6.26 | Client-side Routing |
| Biome | 2.2.2 | Linting & Formatting |
| Vitest | 1.6 | Unit Testing |

### Backend (`python/`)

| Technology | Version | Purpose |
| --- | --- | --- |
| Python | 3.12 | Core Language |
| FastAPI | 0.104+ | Web Framework |
| Uvicorn | 0.24+ | ASGI Server |
| Supabase Client | 2.15.1 | Database Interface |
| AsyncPG | 0.29+ | Async PostgreSQL Driver |
| PydanticAI | 0.0.13+ | AI Agent Framework |
| OpenAI | 1.71.0 | LLM Provider |
| Crawl4AI | 0.7.4 | Web Crawling |
| Sentence Transformers | 4.1+ | Reranking (Optional) |
| Ruff | 0.12.5+ | Linting |
| MyPy | 1.17+ | Type Checking |

### Infrastructure & Database

- **Containerization:** Docker & Docker Compose
- **Database:** Supabase (PostgreSQL 15+)
- **Vector Search:** pgvector (for RAG embeddings)
- **Package Manager (Python):** uv
- **Package Manager (JS):** npm

---

## 3. Architecture Overview

Archon uses a **microservices architecture** with true separation of concerns. Each service is independently deployable and scalable.

### Service Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │  Server (API)   │    │   MCP Server    │    │ Agents Service  │
│                 │    │                 │    │                 │    │                 │
│  React + Vite   │◄──►│    FastAPI +    │◄──►│    Lightweight  │◄──►│   PydanticAI    │
│  Port 3737      │    │    SocketIO     │    │    HTTP Wrapper │    │   Port 8052     │
│                 │    │    Port 8181    │    │    Port 8051    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         └────────────────────────┼────────────────────────┼────────────────────────┘
                                  │                        │
                         ┌─────────────────┐               │
                         │    Database     │               │
                         │                 │               │
                         │    Supabase     │◄──────────────┘
                         │    PostgreSQL   │
                         │    PGVector     │
                         └─────────────────┘
```

### Service Details

| Service | Port | Location | Responsibility |
| --- | --- | --- | --- |
| **Frontend UI** | 3737 | `archon-ui-main/` | React SPA, dashboard, knowledge management UI |
| **API Server** | 8181 | `python/src/server/` | Core business logic, web crawling, RAG, REST endpoints |
| **MCP Server** | 8051 | `python/src/mcp_server/` | MCP protocol interface for AI clients (Cursor, Windsurf) |
| **Agents** | 8052 | `python/src/agents/` | PydanticAI agents, document processing, complex reasoning |
| **Work Orders** | 8053 | `python/src/agent_work_orders/` | (Optional) Workflow execution engine, Claude Code CLI automation |

### Communication Patterns

- **Frontend ↔ Server:** REST API (HTTP) + Smart Polling (ETag caching)
- **AI Client ↔ MCP Server:** MCP Protocol (Server-Sent Events or Stdio)
- **Services ↔ Database:** Direct connection to Supabase (Async via AsyncPG)
- **Inter-service:** HTTP APIs only (No shared code dependencies - true microservices)

---

## 4. Directory Structure

```
archon/
├── archon-ui-main/                  # Frontend Application (React + Vite)
│   ├── src/
│   │   ├── features/                # Vertical Slice Architecture
│   │   │   ├── knowledge/           # Knowledge Base (Crawling, Document Upload)
│   │   │   │   ├── components/
│   │   │   │   ├── hooks/
│   │   │   │   ├── services/
│   │   │   │   └── types/
│   │   │   ├── projects/            # Project & Task Management
│   │   │   │   ├── components/
│   │   │   │   ├── tasks/           # Sub-feature: Task Management
│   │   │   │   ├── documents/       # Sub-feature: Document Management
│   │   │   │   ├── hooks/
│   │   │   │   ├── services/
│   │   │   │   └── types/
│   │   │   ├── mcp/                 # MCP Integration UI
│   │   │   ├── progress/            # Operation Tracking UI
│   │   │   ├── shared/              # Cross-feature Utilities
│   │   │   └── ui/                  # Shared UI Components & Hooks
│   │   ├── components/              # Legacy Components (Migrating to features/)
│   │   ├── services/                # API Clients
│   │   ├── hooks/                   # Custom React Hooks
│   │   ├── pages/                   # Page/Route Components
│   │   └── lib/                     # Utilities
│   ├── vitest.config.ts
│   ├── biome.json
│   └── tailwind.config.js
│
├── python/                          # Backend Monorepo (Python)
│   ├── src/
│   │   ├── server/                  # Main API Server (FastAPI)
│   │   │   ├── main.py              # Entry point, route registration
│   │   │   ├── api_routes/          # REST Endpoints
│   │   │   │   ├── projects_api.py
│   │   │   │   ├── knowledge_api.py
│   │   │   │   ├── tasks_api.py
│   │   │   │   └── ...
│   │   │   ├── services/            # Business Logic
│   │   │   │   ├── project_service.py
│   │   │   │   ├── knowledge_service.py
│   │   │   │   ├── rag_service.py
│   │   │   │   └── ...
│   │   │   ├── models/              # Pydantic Models (Request/Response DTOs)
│   │   │   ├── config/              # Configuration, Database Client
│   │   │   ├── middleware/          # Request/Response Processing
│   │   │   ├── exceptions.py        # Custom Exception Classes
│   │   │   └── utils/               # Shared Utilities
│   │   │
│   │   ├── mcp_server/              # MCP Server Implementation
│   │   │   ├── mcp_server.py        # MCP Entry Point
│   │   │   ├── features/            # MCP Tool Implementations
│   │   │   │   ├── knowledge/       # Knowledge Base Tools
│   │   │   │   ├── projects/        # Project Tools
│   │   │   │   └── ...
│   │   │   └── utils/
│   │   │
│   │   ├── agents/                  # PydanticAI Agents
│   │   │   ├── main.py              # Agent Service Entry
│   │   │   └── features/            # Agent Implementations
│   │   │
│   │   ├── agent_work_orders/       # Workflow Execution (Optional)
│   │   │   └── main.py
│   │   │
│   │   └── __init__.py
│   │
│   ├── tests/                       # Unit Tests
│   │   ├── test_api_essentials.py
│   │   └── ...
│   ├── pyproject.toml               # Dependencies (uv)
│   ├── pytest.ini
│   └── pyrightconfig.json           # Pyright Config
│
├── migration/                       # Supabase SQL Migrations
│   ├── complete_setup.sql           # Initial Schema
│   ├── RESET_DB.sql                 # Full Reset (Dangerous)
│   └── 0.1.0/                       # Versioned Migrations
│       ├── 001_add_source_url_display_name.sql
│       ├── 002_add_hybrid_search_tsvector.sql
│       └── ...
│
├── PRPs/                            # Project Rules & Documentation
│   ├── ai_docs/
│   │   ├── ARCHITECTURE.md          # High-level Architecture
│   │   ├── DATA_FETCHING_ARCHITECTURE.md
│   │   ├── QUERY_PATTERNS.md        # TanStack Query Patterns
│   │   ├── API_NAMING_CONVENTIONS.md
│   │   ├── ETAG_IMPLEMENTATION.md
│   │   └── ...
│   └── templates/
│
├── docker-compose.yml               # Service Orchestration
├── .env.example                     # Environment Variable Template
├── Makefile                         # Development Helpers
├── README.md                        # Setup Instructions
├── CONTRIBUTING.md                  # Contribution Guide
└── LICENSE                          # ACL v1.2
```

---

## 5. Core Features

### 5.1 Knowledge Management

**Purpose:** Ingest and index documentation for RAG.

- **Web Crawling:** Uses `crawl4ai` to recursively crawl documentation sites, sitemaps.
- **Document Processing:** Supports PDF, Docx, Markdown, Text with intelligent chunking.
- **Vector Embeddings:** Stores embeddings in Supabase with pgvector for semantic search.
- **Code Extraction:** Automatically identifies and indexes code examples separately.
- **Hybrid Search:** Keyword-based + semantic search with optional re-ranking.
- **Source Management:** Organize by source (website, uploaded file), type, tags.

**Backend Location:** `python/src/server/services/knowledge_service.py`  
**Frontend Location:** `archon-ui-main/src/features/knowledge/`

### 5.2 Project & Task Management

**Purpose:** Organize work with AI agents.

- **Hierarchical Structure:** Projects → Features → Tasks.
- **Status Tracking:** Todo, Doing, Review, Done.
- **Assignee:** Can be User, Archon AI, or External Agents.
- **Document Management:** Version-controlled documents within projects.
- **Progress Tracking:** Real-time updates via polling.
- **AI-Assisted Generation:** Generate project requirements using AI agents.

**Backend Location:** `python/src/server/services/project_*_service.py`  
**Frontend Location:** `archon-ui-main/src/features/projects/`

### 5.3 MCP Integration

**Purpose:** Expose tools to AI coding assistants.

- **MCP Tools:**
  - `find_documents` / `rag_search_knowledge_base` - Search knowledge base
  - `find_projects` / `manage_project` - Project CRUD
  - `find_tasks` / `manage_task` - Task CRUD
  - And more...
- **Context Sharing:** AI agents can read project state directly.
- **Real-time Updates:** Agents stay in sync with current project state.

**Location:** `python/src/mcp_server/`  
**Default Port:** 8051

### 5.4 AI Agents

**Purpose:** Complex reasoning, document processing.

- **Framework:** PydanticAI
- **Capabilities:**
  - RAG document summarization
  - Code analysis
  - Project generation
  - Custom reasoning workflows
- **Providers:** OpenAI (default), Ollama, Google Gemini

**Location:** `python/src/agents/`  
**Default Port:** 8052

---

## 6. Database Schema (Key Tables)

All tables are in Supabase (PostgreSQL + pgvector).

| Table | Purpose |
| --- | --- |
| `sources` | Metadata for crawled sites and uploaded documents |
| `documents` | Document chunks with text, embeddings (vector), metadata |
| `code_examples` | Extracted code snippets for specialized indexing |
| `archon_projects` | Projects container with features array |
| `archon_tasks` | Task items linked to projects (status: todo/doing/review/done) |
| `archon_document_versions` | Version history for collaborative editing |
| `page_metadata` | Crawled page metadata (title, description, etc.) |

---

## 7. Development Workflow

### Prerequisites

- Docker Desktop
- Node.js 18+
- Supabase Account (Free tier works)
- OpenAI API Key (or Ollama/Gemini)
- (Optional) Make

### Quick Start

1. **Clone & Configure:**
   ```bash
   git clone -b stable https://github.com/coleam00/archon.git
   cd archon
   cp .env.example .env
   # Edit .env: Add SUPABASE_URL and SUPABASE_SERVICE_KEY
   ```

2. **Database Setup:**
   - Log into Supabase dashboard
   - Run `migration/complete_setup.sql` in SQL Editor

3. **Start Services:**
   ```bash
   # Hybrid (Recommended)
   make dev

   # Or Full Docker
   make dev-docker
   ```

4. **Access:**
   - Frontend: http://localhost:3737
   - API: http://localhost:8181
   - MCP: http://localhost:8051

### Common Development Commands

```bash
# Development
make dev                # Hybrid: Backend Docker, Frontend Local (Hot Reload)
make dev-docker         # All services in Docker
make stop               # Stop all services

# Testing
make test               # Run all tests
make test-fe            # Frontend tests only
make test-be            # Backend tests only

# Code Quality
make lint               # Lint frontend (Biome) + backend (Ruff)
make lint-fe            # Frontend only
make lint-be            # Backend only

# Database
# Run in Supabase SQL Editor:
# - migration/RESET_DB.sql (Full reset)
# - migration/complete_setup.sql (Initial setup)

# Environment Check
make check              # Verify setup
make clean              # Remove containers/volumes (with confirmation)
```

### Frontend Commands (in `archon-ui-main/`)

```bash
npm run dev              # Start dev server (Port 3737)
npm run build            # Build for production
npm run lint             # ESLint on legacy code
npm run biome            # Biome check on /src/features
npm run biome:fix        # Auto-fix with Biome
npm run test             # Run tests in watch mode
npm run test:coverage    # Coverage report
```

### Backend Commands (in `python/`)

```bash
uv sync --group all                    # Install dependencies
uv run python -m src.server.main       # Run API server
uv run pytest                          # Run tests
uv run ruff check                      # Lint
uv run ruff check --fix                # Auto-fix
uv run mypy src/                       # Type check
```

---

## 8. Key Architectural Decisions

### Vertical Slices (Frontend)

Each feature owns its entire stack:
- **Feature:** `archon-ui-main/src/features/{feature}/`
- **Structure:** `components/`, `hooks/`, `services/`, `types/`
- **Benefits:** Clear ownership, isolated changes, predictable scaling

### Query-First State Management

- **Server State:** TanStack Query (All data from backend)
- **UI State:** React hooks/Context (Local UI state)
- **No Redux/Zustand:** Reduces boilerplate, single source of truth

### HTTP Polling (No WebSockets)

- **Smart Polling:** Pauses when tab is hidden, adjusts intervals based on focus
- **ETag Caching:** Browser caches responses (~70% bandwidth reduction)
- **Simplicity:** Easier to debug, deploy, and scale

### Direct Database Values

- **No Translation:** Database values (e.g., `"todo"`, `"doing"`) used directly in UI
- **Type Safety:** Zod/TypeScript enforces correctness
- **Simplicity:** Fewer transformation bugs

### Microservices with True Separation

- **No Shared Code:** Each service imports only HTTP clients, never shared libraries
- **Independent Deployments:** Containers built separately
- **Clear APIs:** HTTP-only inter-service communication

---

## 9. API Conventions

### Naming Pattern

```
{METHOD} /api/{resource}/{id?}/{sub-resource?}
```

### Examples

- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project by ID
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `GET /api/projects/{id}/tasks` - Get tasks for project
- `POST /api/projects/{id}/tasks` - Create task in project
- `GET /api/knowledge/search` - RAG search

### Response Format

- **Success:** `{ "data": {...} }`
- **Error:** `{ "error": "message", "code": "ERROR_CODE" }`
- **Status Codes:** 200 (OK), 201 (Created), 400 (Bad Request), 404 (Not Found), 500 (Internal)

---

## 10. Debugging & Troubleshooting

### Common Issues

| Issue | Solution |
| --- | --- |
| Port already in use | Kill process: `lsof -i :PORT` or use different PORT in `.env` |
| Docker permission denied (Linux) | `sudo usermod -aG docker $USER` then logout/login |
| Backend can't connect to DB | Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env` |
| Frontend can't reach backend | Verify backend running: `curl http://localhost:8181/health` |
| Hot reload not working | Ensure hybrid mode: `make dev` (not `make dev-docker`) |
| Docker hangs | `docker compose down --remove-orphans && docker system prune -f` |

### Logs

```bash
# View all service logs
docker compose logs -f

# Specific service
docker compose logs -f archon-server    # API Server
docker compose logs -f archon-mcp       # MCP Server
docker compose logs -f archon-ui        # Frontend
docker compose logs -f archon-agents    # Agents Service
```

### Health Checks

```bash
# API Server Health
curl http://localhost:8181/health

# MCP Server Health
curl http://localhost:8051/health

# Database Connection Test (from Python)
cd python
uv run python -c "from src.server.config.database import get_db; print('DB OK')"
```

---

## 11. Important Notes for Development

- **Beta Status:** Expect bugs, contribute fixes, not workarounds.
- **Fix-Forward:** No backward compatibility; remove deprecated code immediately.
- **Error Handling:** Fail fast and loud for initialization errors; complete batch jobs with detailed error logs.
- **Code Organization:** Keep files 500-1000 lines; split into modules if approaching limit.
- **Logging:** Use structured logging with context (IDs, URLs, timestamps).
- **Testing:** Unit tests for all new features; mock services, not implementation.
- **Security:** Validate inputs, use parameterized queries, handle sensitive data securely.
- **Performance:** Monitor query performance, use caching where appropriate.

---

## 11.5 Recent Implementation Status (December 2025)

### Completed Features

#### Fault-Tolerant Job Tracking System
- **Watchdog Background Task:** Supervisor monitors stale jobs (heartbeat > 2 mins) and automatically recovers them by resetting status to `pending` (up to `max_retries` attempts).
- **Database Schema:** Added `total_pending` column to `crawl_states` for efficient quantification of pending work without parsing large JSON arrays.
- **Checkpoint Mechanism:** Workers now update `total_pending` during checkpoints for accurate progress visualization.
- **Files Modified:**
  - `python/src/workers/supervisor.py` - Added `run_watchdog()` and `recover_job()` methods
  - `python/src/server/services/crawling/crawling_service.py` - Updated checkpoint callback to track `total_pending`
  - `migration/0.1.0/013_add_total_pending_column.sql` - New migration for schema update

#### Pause/Resume Functionality with Database-Driven State Sync
- **API-Side Fallback:** `pause_crawl_task` and `resume_crawl_task` endpoints now fallback to database status updates if task is not in memory (worker processes).
- **Worker-Side Monitoring:** Added `_monitor_job_status()` background task to `CrawlingService` that polls DB every 2 seconds and syncs internal pause/resume state.
- **Bidirectional Communication:** API updates DB → Worker detects change → Worker pauses/resumes execution.
- **Files Modified:**
  - `python/src/server/api_routes/knowledge_api.py` - Updated pause/resume endpoints with DB fallback
  - `python/src/server/services/crawling/crawling_service.py` - Added status monitor and integrated into `execute_crawl_job()`

#### Paused Operations Visibility in Active Operations List
- **Progress API Enhancement:** Updated `list_active_operations()` to include `paused` status when querying database.
- **Progress Detail Endpoint:** Updated `get_progress()` to fetch and display progress state for both `processing` and `paused` jobs.
- **UI Message:** Paused jobs now show "Paused at X/Y pages..." with accurate progress percentage.
- **Files Modified:**
  - `python/src/server/api_routes/progress_api.py` - Added `paused` status to active operations queries

#### Enhanced UI Status Visualization
- **Progress Component:** Added `PauseCircle` icon and orange/yellow color coding for `paused` status in `KnowledgeCardProgress`.
- **Card Component:** Updated `KnowledgeCard` to apply orange edge color and yellow accent when operation is paused.
- **Visual Differentiation:** Paused cards now clearly distinguished from running (cyan), failed (red), and processing (orange) states.
- **Files Modified:**
  - `archon-ui-main/src/features/progress/components/KnowledgeCardProgress.tsx` - Added paused status handling
  - `archon-ui-main/src/features/knowledge/components/KnowledgeCard.tsx` - Updated color logic for paused state

### Known Limitations & Next Steps

- **Worker Restart Handling:** If a Worker process crashes during a paused job, the Watchdog will eventually recover it (after heartbeat timeout). This is expected behavior for beta.
- **Resume Persistence:** When resuming a paused job in a Worker, it will continue from the last checkpoint. Ensure migrations are applied before restarting services.
- **Progress Quantification:** `total_pending` optimization is optional; UI gracefully falls back to calculating from frontier if column missing.

### Migration Instructions

To enable all new features, apply the following migrations in Supabase SQL Editor:

1. Run `migration/0.1.0/013_add_total_pending_column.sql` to add the new column
2. Restart backend services: `docker compose restart archon-server`
3. Paused operations will now be visible in the Active Operations list

### Testing Recommendations

- **Test Pause:** Start a crawl, wait 10+ seconds, click Pause. Verify operation appears in Active Operations with "Paused" badge.
- **Test Resume:** Click Resume on a paused operation. Verify it continues from the saved checkpoint without restarting.
- **Test Watchdog:** Stop a Worker process mid-crawl (simulate crash). Wait 2+ minutes. Verify Watchdog automatically recovers the job.
- **Test Restart:** Pause a job, restart backend. Verify paused operation is still visible and resumable.

---

## 12. Deployment

### Development
- **Hybrid (Recommended):** `make dev` (Frontend hot-reload)
- **Full Docker:** `make dev-docker`

### Production
- Build all containers: `docker compose up --build -d`
- Run migrations in Supabase SQL Editor
- Set appropriate environment variables in `.env`
- Access at configured URL/Port

---

## 13. Resources

- **GitHub:** https://github.com/coleam00/archon
- **Discussions:** https://github.com/coleam00/Archon/discussions
- **Kanban:** https://github.com/users/coleam00/projects/1
- **Setup Video:** https://youtu.be/DMXyDpnzNpY
- **License:** ACL v1.2 (Free, open-source)

---

**Last Updated:** December 16, 2025 (Fault Tolerance & Pause/Resume Implementation)  
**Archon Version:** 0.1.0 (Beta)  
**Key Recent Changes:** Watchdog recovery system, pause/resume with DB state sync, paused operations visibility, enhanced UI status differentiation
