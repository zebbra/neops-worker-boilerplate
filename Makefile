sync:
	uv sync

# Ruff discovers its own files from `include` in pyproject.toml
# (my_worker, tests, scripts). Keep these bare so the config stays the
# single source of truth.
lint:
	uv run ruff format --check
	uv run ruff check

lint-fix:
	uv run ruff format
	uv run ruff check --fix

format:
	uv run ruff format

# Bare pyrefly, no baseline: this project starts at 0 errors and stays there.
typeCheck:
	uv run pyrefly check ./my_worker ./tests ./scripts

audit:
	# Scope to the runtime dependency closure. pip-audit pulls `pip-api`
	# -> `pip`, and scanning the audit toolchain itself produces noise
	# without security signal. Exporting `--no-dev` requirements first
	# scopes the scan to what actually ships. pip-audit skips the
	# scrapli-cfg git requirement itself.
	uv export --no-dev --no-hashes -o /tmp/my-worker-prod-reqs.txt
	uv run pip-audit --disable-pip --no-deps --skip-editable \
		-r /tmp/my-worker-prod-reqs.txt

test:
	uv run pytest -q

# Start the worker against the engine configured in .env
# (cp .env.dist .env first; neops_worker_sdk loads .env itself via python-dotenv).
run:
	@test -f .env || { echo "No .env found — run: cp .env.dist .env"; exit 1; }
	uv run neops_worker

# Docker build helpers. No build secrets or tokens — this project is pure Python.
#
#   make build-docker                    # the runtime image, exactly as CI builds it
#   make build-docker IMAGE_NAME=foo     # tag it foo:latest instead
#
# build-docker mirrors CI: default target, context `.`, no build args
# (.github/workflows/ci.yml).
IMAGE_NAME ?= my-worker

build-docker:
	docker build -t $(IMAGE_NAME):latest .

# One-time: rename the my_worker/my-worker placeholders to your project's name.
#
#   make init-repo NAME=acme_worker
#
# Requires a clean git tree; leaves the rename uncommitted for review.
init-repo:
	python3 scripts/init_repo.py $(NAME)
