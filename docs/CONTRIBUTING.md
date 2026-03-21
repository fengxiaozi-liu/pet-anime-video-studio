# Contributing to Pet Anime Video

Thank you for your interest in contributing! Here's how to get started.

---

## Development Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/pet-anime-video.git
cd pet-anime-video

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example backend/.env
# Edit backend/.env with your API keys

# 5. Run the development server
python backend/main.py
```

---

## Running Tests

```bash
# Run all tests
cd backend && pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_jobs.py -v

# Run in watch mode (requires pytest-watch)
ptw tests/
```

---

## Code Style

We use standard Python tooling:

```bash
# Format code
black backend/app

# Check formatting
black --check backend/app

# Lint
flake8 backend/app
```

**Rules**:
- Max line length: 100 characters
- Use type hints where practical
- docstrings for public functions
- No trailing whitespace

---

## Project Structure

```
backend/
├── app/
│   ├── main.py         # FastAPI app and routes
│   ├── config.py       # Settings / environment config
│   ├── jobs.py         # Job store (JSON-backed)
│   ├── assets.py       # Asset store
│   ├── pipeline.py     # Video generation pipeline
│   ├── schema.py       # Pydantic request/response models
│   ├── security.py     # Auth and rate limiting
│   ├── platform_templates.py  # Platform preset definitions
│   └── providers/      # AI provider integrations
│       ├── base.py
│       ├── kling_provider.py
│       ├── openai_provider.py
│       ├── gemini_provider.py
│       ├── doubao_provider.py
│       └── local_provider.py
└── tests/
    ├── conftest.py      # Shared pytest fixtures
    ├── test_jobs.py
    ├── test_assets.py
    ├── test_pipeline.py
    └── ...
```

---

## Submitting Changes

### Workflow

1. **Fork** the repository
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** — add tests for new functionality
4. **Run tests** to ensure nothing is broken:
   ```bash
   pytest backend/tests/ -v
   ```
5. **Commit** with a clear message:
   ```bash
   git commit -m "Add retry logic for Kling API timeouts"
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** on GitHub

### Commit Message Format

```
type: short description

Longer explanation if needed. Wrap at 100 chars.

Fixes #123
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Checklist

- [ ] Tests pass (`pytest backend/tests/ -v`)
- [ ] Code is formatted (`black backend/app`)
- [ ] New endpoints have docstrings
- [ ] New configuration options documented in `docs/CONFIGURATION.md`
- [ ] No debug prints or commented-out code

---

## Areas to Contribute

Looking for something to work on? Check the GitHub Issues for:

- 🟢 **Good first issues** — small, self-contained tasks
- 🟡 **Enhancements** — new features, API improvements
- 🔴 **Backend tasks** — provider integrations, pipeline improvements

---

## Questions?

- Open an issue on GitHub
- Check existing documentation in `docs/`
