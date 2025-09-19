# Repository Guidelines

## Project Structure & Module Organization
`app.py` boots the Flask service using `config.py`. Feature blueprints sit in `routes/`,
supporting logic in `services/`, and data models in `models/`. Shared helpers stay in
`utils/` and `extensions.py`. Templates, static assets, and fonts live in `templates/`
and `static/`. Operational scripts reside in `scripts/`, `migrations/`, and curated
maintenance modules at the repo root. Tests mirror production features under `tests/`
so coverage stays discoverable.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: create and activate a virtual
  environment (`venv\\Scripts\\activate` on Windows).
- `pip install -r requirements.txt`: install runtime dependencies.
- `pip install -r requirements-dev.txt`: add dev tooling such as `pytest`.
- `flask run`: start the API after exporting `FLASK_APP=app.py` and required secrets.
- `flask db migrate` / `flask db upgrade`: manage Alembic migrations.
- `pytest`: execute the suite; `pytest tests/test_<area>.py` scopes to a feature.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and keep lines under 88 characters. Use
snake_case for modules and functions, PascalCase for classes, and UPPER_SNAKE_CASE for
constants. Update `utils/endpoints.py` whenever a dashboard route changes so
redirects remain synchronized. Write concise docstrings for public components and
favor descriptive identifiers over abbreviations.

## Testing Guidelines
Pytest is configured via `tests/conftest.py`. Create new files as `test_<scenario>.py`
and prefix test functions with `test_`. Cover success and failure paths around
scheduling, reviewer workflows, payments, and dashboards. Prefer in-memory SQLite
fixtures and avoid mutating shared sample data. Run `pytest` before every pull request
and confirm new fixtures are deterministic.

## Commit & Pull Request Guidelines
Keep commits small, focused, and written in the imperative mood (e.g., `Add usage_count
to monitor link tracking`). Reference related tickets in the body when relevant and
avoid bundling fixes. Pull requests should include a summary, testing notes, linked
issues, and screenshots for UI updates. Flag database migrations or configuration
changes so reviewers can stage safely.

## Configuration Notes
Environment variables from `.env.example`—`SECRET_KEY`, Google OAuth keys, database
URLs, and Mailjet credentials—must be present before running Flask. Keep secrets out of
version control by using a local `.env` file or shell exports. Re-run `python
scripts/executar_formulario_trabalhos.py` whenever the default Formulario de Trabalhos
needs to be recreated.
