# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AutoScoring** is a Flask web application for automatic grading of student lab reports/assignments using Large Language Models (LLMs). It's designed for Lab FKI Universitas Muhammadiyah Surakarta and supports multiple LLM providers (Gemini, OpenAI, NVIDIA, DeepSeek, OpenRouter, SiliconFlow, GitHub Models).

### Key Capabilities
- **Bulk & Single Processing**: Grade up to 50 files in batch or one at a time
- **Multi-Provider LLM**: Configurable via Admin Panel (Gemini with round-robin API key rotation, or OpenAI-compatible providers)
- **Document Parsing**: PDF extraction via Docling with optional EasyOCR for scanned documents
- **GPU Acceleration**: Supports NVIDIA GPU for faster OCR processing
- **Real-time Status**: Track processing progress with WebSocket-like polling
- **Database-backed Config**: Runtime settings persist in SQLite (`llm_config` table)
- **Role-based Access**: Admin and Aslab (lab assistant) roles with Flask-Login

---

## Development & Deployment

### Local Development

```bash
# Create and activate Python 3.10+ virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY, LLM_PROVIDER, API keys, etc.

# Run application (dev server on port 5005)
python run.py

# Run tests
python -m pytest tests -v
python -m pytest tests/test_scoring_service.py -v  # Single test file
python -m pytest tests/test_scoring_service.py::TestScoring::test_extract_student_info -v  # Single test
```

### Docker Deployment

```bash
# GPU-enabled (recommended with NVIDIA GPU)
docker-compose up -d --build
# CPU-only
docker-compose -f docker-compose.cpu.yml up -d --build
# Both run on port 5005 (mapped to 80 in production via nginx)
```

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd.yml`):
1. **test** job: Runs `pytest` on push/PR to main/master
2. **deploy_cpu** job: Deploys to VPS after tests pass (main/master only)
3. **notify_discord** job: Posts deployment summary to Discord (optional)

**Deploy secrets required** in GitHub environment `autoscore`:
- `VPS_HOST`, `VPS_USER`, `VPS_PROJECT_PATH`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS`
- Optional: `DISCORD_WEBHOOK_URL`

---

## Architecture

### Layer Structure

```
routes/
├── dashboard.py       # Main UI endpoints (bulk/single upload, status, CSV download)
├── auth.py           # Login/logout, user management
└── admin_views.py    # Flask-Admin customization (user/config/log management)

services/
├── scoring_service.py       # Orchestrates PDF→LLM→CSV pipeline
├── llm_service.py           # Unified interface for 7 LLM providers
├── docling_service.py       # PDF parsing & text extraction
├── cleanup_service.py       # Periodic file cleanup (2 AM daily)
└── runtime_settings_service.py  # DB-backed runtime config sync

models.py              # SQLAlchemy models (User, Job, JobResult, LLMConfig)
config.py              # Flask config + environment variable loading
extensions.py          # SQLAlchemy, login manager, CSRF, scheduler init
```

### Data Model

- **User**: Admin/Aslab role, login credentials
- **Job**: Bulk or single scoring request, tracks status/files/results
- **JobResult**: Individual student result within a Job (NIM, name, score, evaluation)
- **LLMConfig**: Key-value store for runtime LLM settings (provider, model, API keys) — persists across restarts
- **SystemLog** (optional): Audit trail for admin actions

### Processing Pipeline

1. **Upload** → Store files in `instance/uploads/{job_id}/`
2. **Parse** → Docling extracts text from PDF/images
3. **Score** → LLM evaluates student answer against reference (answer key/question/notes)
4. **Store** → Save results to DB and export CSV
5. **Cleanup** → APScheduler removes temp files daily at 2 AM

---

## Configuration & Environment

### Environment Variables (`.env`)

```bash
# Flask
SECRET_KEY=your-secure-random-key

# Database (defaults to SQLite)
DATABASE_URL=sqlite:///autoscoring.db

# File Limits
MAX_FILE_SIZE_MB=50
MAX_PDF_COUNT=50

# Scoring
DEFAULT_SCORE_MIN=40
DEFAULT_SCORE_MAX=100
EVALUATION_MAX_WORDS=100

# Processing
MAX_WORKERS=4
MAX_RETRIES=3
ENABLE_OCR=true
ENABLE_CLEANUP=true
CLEANUP_ON_STARTUP=true

# LLM Provider (initial; can change via Admin Panel)
LLM_PROVIDER=gemini  # or: nvidia, openai, deepseek, openrouter, siliconflow, github
LLM_MODEL=gemini-2.5-flash

# Gemini (supports up to 20 keys for round-robin)
GEMINI_API_KEY_1=your-key
GEMINI_API_KEY_2=...

# OpenAI-compatible providers
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=nvapi-...
DEEPSEEK_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
SILICONFLOW_API_KEY=sk-...
GITHUB_API_KEY=ghp_...
```

### Runtime Settings (Admin Panel)

Settings in **Admin > Pengaturan LLM** are stored in the `llm_config` table and automatically synced to Flask config every 30 seconds (configurable via `RUNTIME_SETTINGS_REFRESH_TTL_SEC`). Keys:
- `llm_provider`, `llm_model`
- `{provider}_api_key`, `{provider}_base_url` for OpenAI-compatible providers
- `gemini_api_keys` (JSON array for round-robin)

---

## Key Components

### LLM Service (`llm_service.py`)

Abstraction layer over Gemini and OpenAI-compatible APIs:
- **Providers**: Gemini, NVIDIA, OpenAI, DeepSeek, OpenRouter, SiliconFlow, GitHub Models
- **Round-robin**: For Gemini, rotates through up to 20 API keys to avoid rate limits
- **Unified interface**: `score()` method handles all provider logic internally
- **Config resolution**: Reads from DB (`llm_config` table) or `.env`

### Scoring Service (`scoring_service.py`)

Orchestrates the full pipeline:
- **Threading**: Uses `ThreadPoolExecutor` to process multiple students in parallel
- **Lazy initialization**: DoclingService and LLMService initialized on first use (thread-safe)
- **Progress tracking**: Updates in-memory dict + database `JobResult` status
- **Retry logic**: Configurable retries with exponential backoff
- **Error handling**: Marks failed results with error messages; logs via `SystemLog`

### Docling Service (`docling_service.py`)

PDF parsing and extraction:
- **Text extraction**: Docling for structured/scanned PDFs
- **OCR fallback**: EasyOCR for image-based or highly formatted documents
- **GPU support**: Auto-detects CUDA; uses GPU if available
- **Image handling**: Removes base64/image placeholders to reduce token usage

---

## Testing

### Test Structure

```
tests/
├── conftest.py                          # Pytest fixtures (test app, DB, auth)
├── test_auth.py                         # Login/logout flows
├── test_dashboard_routes.py             # Upload, progress, download endpoints
├── test_scoring_service.py              # Core scoring pipeline (mocked LLM)
├── test_llm_service_providers.py        # Provider abstraction
├── test_docling_service.py              # PDF parsing
├── test_single_processing.py            # Single student flow
├── test_llm_settings_view.py            # Admin LLM config UI
└── test_models.py                       # Database model tests
```

### Running Tests

```bash
# All tests
pytest tests -v

# With coverage
pytest tests --cov=app --cov-report=html

# Skip slow tests (GPU/real API)
pytest tests -v -m "not slow"

# Watch mode (with pytest-watch)
ptw tests
```

### Test Database

Tests use an in-memory SQLite database (configured in `conftest.py`) to avoid polluting production DB.

---

## Common Development Tasks

### Adding a New LLM Provider

1. Update `llm_service.py`:
   - Add provider name to `OPENAI_COMPAT_PROVIDERS` or handle separately for Gemini
   - Add default model to `DEFAULT_MODELS`
   - Add API key field to `PROVIDER_KEY_FIELDS`
   - Add base URL to `PROVIDER_BASE_URLS`
2. Update `config.py`:
   - Add `{PROVIDER}_API_KEY` env var
   - Add `{PROVIDER}_BASE_URL` env var
3. Update `.env.example` with new variables
4. Test with `test_llm_service_providers.py`

### Modifying Scoring Logic

1. **System prompt**: Edit `SYSTEM_PROMPT` in `llm_service.py` (affects all providers)
2. **JSON parsing**: Update regex in `llm_service.py`'s `_parse_response()` method
3. **Retry logic**: Adjust `MAX_RETRIES` in `.env` or `max_retries` in `ScoringService`

### Changing Database Schema

Use lightweight migrations in `app/__init__.py`'s `apply_schema_patches()` function (idempotent ALTER TABLE statements). Or use a proper migration tool (Alembic) for complex changes.

### Troubleshooting Deployment

- **Logs**: Check `logs/autoscoring.log` on VPS or in Docker container (`docker logs <container-id>`)
- **Database issues**: SSH to VPS, inspect `instance/autoscoring.db` with `sqlite3`
- **GPU detection**: Verify `nvidia-smi` on host; check `CUDA_VISIBLE_DEVICES` in docker-compose
- **OCR slowness**: Profile with `ENABLE_OCR=false` to isolate bottleneck

---

## Code Conventions

### Naming & Structure

- **Routes**: `blueprint_name.route('/path')` with clear function names
- **Services**: Stateful classes (e.g., `ScoringService`) for orchestration; pure functions for utilities
- **Models**: Use SQLAlchemy declarative model pattern with relationships
- **Config**: Environment variables in `config.py`, runtime settings in DB (`llm_config`)

### Error Handling

- Routes catch exceptions and return JSON error responses with 400/500 status
- Services log errors with `logger.error()` and raise custom exceptions (or propagate) for caller to handle
- Database errors rollback transaction and log warning; graceful fallback when possible

### Logging

- Use `logger = logging.getLogger(__name__)` per module
- Log levels: INFO for user actions, WARNING for retries/degraded mode, ERROR for failures
- All logs go to `logs/autoscoring.log` (rotating, 10 MB max) and console in debug mode

### Testing

- Use pytest fixtures for setup/teardown (see `conftest.py`)
- Mock external APIs (LLM, Docling) to avoid rate limits
- Test both happy path and error cases (missing files, API timeouts, DB issues)

---

## Known Limitations & Notes

1. **In-memory job progress**: `job_progress` dict in `dashboard.py` is not persistent across restarts. For production, migrate to Redis.
2. **Threading in Flask**: Using `ThreadPoolExecutor` works but consider Celery for truly async jobs at scale.
3. **GPU memory**: EasyOCR loads large models; ensure sufficient VRAM (8GB+ recommended).
4. **Rate limits**: Gemini round-robin helps but may still hit quotas; monitor `llm_service.py` logs for fallback behavior.
5. **Filename extraction**: NIM/name detection relies on filename patterns (e.g., `[NIM]_[Name]_*.pdf`); document this in user guide.

---

## Default Credentials

⚠️ **Change immediately in production:**
- Username: `admin`
- Password: `informatika` (or set via `ADMIN_PASSWORD` env var)

---

## Resources

- **README.md**: Feature overview, deployment guide, configuration table
- **.github/workflows/ci-cd.yml**: GitHub Actions test and deploy jobs
- **docker-compose.yml / docker-compose.cpu.yml**: Docker service definitions
- **requirements.txt**: Python dependencies
