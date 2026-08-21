#!/usr/bin/env python3
"""One-time repo initialisation: rename the boilerplate placeholders to a real project name.

Usage (via make):

    make init-repo NAME=acme_worker

Renames the placeholder python package directory to ``<name>/`` and rewrites the
snake_case (``<placeholder>``) and kebab-case (``<place-holder>``) tokens across
all git-tracked text files: pyproject name, README title, Dockerfile,
.env.dist, CI workflow, FB package ``fb.<place-holder>.example.io``, imports
and tests. ``uv.lock`` is not rewritten — it is regenerated with ``uv lock``
at the end. Everything is left uncommitted for review.

The absence of the placeholder in the tree is the "already initialised" marker,
which is also why this file spells the placeholder tokens only in a computed
form: after a rename the script survives verbatim and simply refuses to run
again.
"""

import keyword
import re
import subprocess
import sys
from pathlib import Path

# Computed so this script carries no literal occurrence of the placeholder
# (see module docstring).
PLACEHOLDER_SNAKE = "_".join(("my", "worker"))
PLACEHOLDER_KEBAB = "-".join(("my", "worker"))

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

REPO_ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [REPO_ROOT / entry for entry in output.split("\0") if entry]


def main(argv: list[str]) -> int:
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout:
        return fail("working tree is not clean — commit or stash your changes first (init-repo rewrites tracked files)")

    if len(argv) != 1 or not argv[0]:
        return fail("NAME is required — usage: make init-repo NAME=<name>")

    name = argv[0]
    if not NAME_RE.match(name):
        return fail(f"invalid NAME {name!r} — must be a lowercase python identifier matching {NAME_RE.pattern}")
    if keyword.iskeyword(name):
        return fail(f"invalid NAME {name!r} — python keywords cannot be package names")
    if name == PLACEHOLDER_SNAKE:
        return fail(f"NAME equals the placeholder {PLACEHOLDER_SNAKE!r} — pick your project's real name")

    name_kebab = name.replace("_", "-")

    files = tracked_files()
    lock_file = REPO_ROOT / "uv.lock"

    rewritable: list[tuple[Path, str]] = []
    for path in files:
        if path == lock_file:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if PLACEHOLDER_SNAKE in content or PLACEHOLDER_KEBAB in content:
            rewritable.append((path, content))

    package_dir = REPO_ROOT / PLACEHOLDER_SNAKE
    if not rewritable and not package_dir.is_dir():
        return fail(f"already initialized — the {PLACEHOLDER_SNAKE!r} placeholder no longer occurs in this repo")

    target_dir = REPO_ROOT / name
    if package_dir.is_dir() and target_dir.exists():
        return fail(f"cannot rename {PLACEHOLDER_SNAKE}/ — {name}/ already exists")

    for path, content in rewritable:
        updated = content.replace(PLACEHOLDER_SNAKE, name).replace(PLACEHOLDER_KEBAB, name_kebab)
        path.write_text(updated, encoding="utf-8")
        print(f"rewrote  {path.relative_to(REPO_ROOT)}")

    if package_dir.is_dir():
        package_dir.rename(target_dir)
        print(f"renamed  {PLACEHOLDER_SNAKE}/ -> {name}/")

    print("relocking uv.lock ...")
    subprocess.run(["uv", "lock"], cwd=REPO_ROOT, check=True)

    print()
    print(f"Initialized as {name!r} ({len(rewritable)} file(s) rewritten). Nothing has been committed:")
    print("  1. review the changes:  git status && git diff")
    print("  2. refresh the venv:    uv sync")
    print("  3. verify:              make lint typeCheck test")
    print("  4. commit:              git add -A && git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
