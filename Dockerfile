# my-worker runtime image — modeled on the neops-worker-sdk Dockerfile,
# without its CI stages (linting/tests run in CI directly, see
# .github/workflows/ci.yml).

# base container
FROM python:3.12.7 AS base

# install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# set the working directory in the container
WORKDIR /app

# copy the dependency files into the container
COPY ./uv.lock ./
COPY ./pyproject.toml ./
# hatchling reads `readme = "README.md"`; the project install below fails without it.
COPY ./README.md ./

# set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# install virtual environment and dependencies
# (deps-only first, for layer caching; the scrapli-cfg git dependency is
# cloned here, which is why this stage needs the full python image's git)
RUN uv sync --frozen --no-dev --no-install-project

# The function blocks (fb.my-worker.example.io/*) live here. Without them the
# image has no function blocks to register — see DIR_FUNCTION_BLOCKS below,
# which is resolved relative to WORKDIR (`my_worker/fb` -> /app/my_worker/fb).
COPY ./my_worker my_worker/

# Install the project (the sync above is deps-only, for layer caching). Without
# this, `uv run` builds and installs it at every container start instead.
RUN uv sync --frozen --no-dev

# Where the worker scans for function blocks. URL_BLACKBOARD (and optionally
# WORKER_NAME etc. — see .env.dist) must be provided at `docker run` time.
ENV DIR_FUNCTION_BLOCKS=my_worker/fb

# --no-sync: the build already installed everything.
CMD ["uv", "run", "--no-sync", "neops_worker"]
