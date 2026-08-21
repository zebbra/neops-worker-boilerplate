# my-worker

Boilerplate for a NeOps worker that ships custom function blocks, built on
[`neops_worker_sdk`](https://pypi.org/project/neops-worker-sdk/) (pinned to `0.2.0b4`).

A function block ("FB") is a typed, testable unit of automation: Pydantic
parameters in, Pydantic result out, executed by a worker process that polls the
NeOps workflow engine's blackboard API for jobs.

## Quick start

```bash
uv sync                 # install everything (dev tools included)
make lint               # ruff format --check + ruff check
make typeCheck          # pyrefly, must stay at 0 errors
make test               # pytest over tests/
```

Run the worker against a local engine (e.g. the `neops-lab` containerlab stack,
which exposes the workflow engine on `localhost:3030`):

```bash
cp .env.dist .env       # URL_BLACKBOARD, WORKER_NAME, DIR_FUNCTION_BLOCKS
make run                # uv run neops_worker — registers the FBs and polls for jobs
```

Build the runtime image (same build CI does):

```bash
make build-docker       # -> my-worker:latest
docker run --rm --add-host=host.docker.internal:host-gateway \
    -e URL_BLACKBOARD=http://host.docker.internal:3030 my-worker:latest
```

(The `--add-host` flag is required on Linux, where `host.docker.internal` does
not resolve by default; alternatively use `--network host` with
`URL_BLACKBOARD=http://localhost:3030`.)

## Make this repo yours: `make init-repo`

The python package `my_worker/`, the pyproject name `my-worker` and the FB
package `fb.my_worker.example.io` are deliberate placeholders. After your first
commit, rename them all in one step:

```bash
make init-repo NAME=acme_worker
```

The script requires a clean git tree, renames `my_worker/` to `acme_worker/`,
rewrites every `my_worker` / `my-worker` occurrence across tracked files,
regenerates `uv.lock`, and leaves everything uncommitted for you to review
(`git diff`), `uv sync`, verify (`make lint typeCheck test`) and commit. It
refuses to run twice — once the placeholder is gone, the repo counts as
initialized.

Also pick a real FB package name: after the rename the FB package is
`fb.acme_worker.example.io` — change `example.io` to your domain by hand; the
NeOps convention is a DNS-style namespace like `fb.base.neops.io`. Note the
underscore: the engine's workflow schema forbids hyphens in function-block
identifiers (`RootWorkflow.schema.json` pattern `^([^/:-]+)\/([^/:-]+):…`),
so keep every segment of the FB package hyphen-free.

## Writing a function block

Three examples live in `my_worker/fb/`, in ascending order of ceremony:

- **`hello_world.py`** — the smallest possible FB: typed params
  (`FunctionBlockParams`), typed result (`FunctionBlockResultData`),
  `@register_function_block` + `Registration`, no device, no entities.
- **`device_interface_report.py`** — a device-scoped FB showing `acquire()`
  (requesting the device's interfaces into the job context with an
  `EntityAcquireByElasticQuery`), parameter validation via Pydantic `Field`
  constraints, and reading entities from the `WorkflowContext` — all without
  opening a device connection.
- **`connection_test.py`** — a device-scoped FB that actually opens a
  connection: `NetworkDeviceDiscoveryProxy.connect(device, "ssh")` +
  `get_information()`, wrapped in `@run_in_thread` because netmiko I/O is
  blocking. Run it via the `simple_test_connection` workflow (below) to prove
  worker-to-device connectivity end to end.

Every FB is addressed by `"<package>/<name>:<major.minor.patch>"`, e.g.
`fb.my_worker.example.io/hello_world:0.1.0`. Workflow definitions pin that
exact identifier — renaming or version-bumping an FB breaks every workflow
that names it, with no compile-time check. Bump deliberately.

The worker discovers FBs by scanning the directories in `DIR_FUNCTION_BLOCKS`
(comma-separated; `my_worker/fb` here) — a new FB only needs a new module in
that tree, the `@register_function_block` decorator does the rest.

Tests mirror the SDK's own pattern: instantiate the FB and call
`execute_function_block(params=..., context=..., propagate_exceptions=True)`
with a context built by the SDK's
`neops_worker_sdk.testing.factories.context_factory.create_workflow_context` —
see `tests/`.

## The `simple_test_connection` workflow

`workflows/simple_test_connection.workflow.yaml` is a device-scoped workflow
(`seedEntity: device` — the engine fans out one job per device in scope) whose
single step runs `fb.my_worker.example.io/test_connection:0.1.0`. Use it as the
first end-to-end proof against a running stack (e.g. `neops-lab`): start
`make run`, register the workflow, execute it from the engine UI
(`localhost:3031` in the lab), and every device in scope reports its hostname,
vendor and software release.

### Registering the workflow

Workflows are registered by POSTing `{"workflow": <parsed yaml>}` to the
engine's publish route (the same contract `neops-lab/bootstrap/register.py`
uses):

```bash
uv run python -c "
import json, pathlib, urllib.request, yaml
wf = yaml.safe_load(pathlib.Path('workflows/simple_test_connection.workflow.yaml').read_text())
req = urllib.request.Request('http://localhost:3030/workflow-definition/publish',
    data=json.dumps({'workflow': wf}).encode(), headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req).status)
"
```

`201` = published, `200` = already published unchanged. Published versions are
immutable: a `409` means this version already exists with different content —
bump `majorVersion`/`minorVersion`/`patchVersion` in the YAML instead of
editing in place (and keep the FB identifier in the step in sync with the FB's
`Registration.version`).

## Dependency notes

- **`neops_worker_sdk==0.2.0b4`** is exact-pinned: the SDK is in beta and its
  generated engine client (`neops_workflow_engine_client`) must match the
  engine's REST contract. Bump the pin consciously, not via lockfile drift.
- **`scrapli-cfg` git pin**: the SDK's Cisco IOS scrapli config operations need
  scrapli-cfg, but no PyPI release of it is compatible with
  `scrapli>=2026.2.20`, and PyPI forbids git URLs in published metadata — so
  the SDK cannot carry the pin for you (it keeps it in a non-published `fb`
  dependency group). An end project like this one can, and this dependency
  mirrors exactly that group. If none of your FBs touch IOS devices, you can
  drop it.

## Layout

```
my_worker/fb/           function blocks (scanned via DIR_FUNCTION_BLOCKS)
workflows/              workflow definitions to publish to the engine
tests/                  FB tests (pytest, asyncio_mode=auto)
scripts/init_repo.py    the one-time rename script behind `make init-repo`
.env.dist               environment template — cp to .env
Dockerfile              runtime image; ships my_worker/ and runs neops_worker
.github/workflows/      lint-audit-typecheck-test + docker build (no push)
```
