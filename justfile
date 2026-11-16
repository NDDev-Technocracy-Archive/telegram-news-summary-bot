set minimum-version := "1.59.0"
set dotenv-load := false
set default-list

# Install the existing application requirements and source checker in an isolated environment.
setup:
    uv venv --allow-existing --no-python-downloads .venv
    uv pip install --python .venv/bin/python -r requirements.txt -r tools/requirements-checks.txt

# Check tracked Python syntax and the existing lint policy without network access.
check:
    just --fmt --check
    python3 tools/check-source.py
    .venv/bin/ruff check .
    git diff --check

# Apply the existing Python linter's automatic fixes.
fix:
    just --fmt
    .venv/bin/ruff check --fix .

# Verify byte-compilation without starting Telegram, scraping or a model client.
test:
    .venv/bin/python -m compileall -q src tools

# Run the complete source and byte-compilation checks.
verify: check test
