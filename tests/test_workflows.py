"""Every workflow in workflows/ names a function block this repo registers, at its version.

Renaming or re-versioning a block breaks the workflows that name it only at run time,
as "Function block not found"; this catches it before a publish.
"""

from pathlib import Path

import pytest
import yaml
from neops_worker_sdk.registry import registry

import my_worker.fb.connection_test
import my_worker.fb.device_interface_report
import my_worker.fb.hello_world  # noqa: F401

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / "workflows").glob("*.workflow.yaml"))


def _function_blocks(workflow: Path) -> list[str]:
    steps = yaml.safe_load(workflow.read_text())["steps"]
    return [step["functionBlock"] for step in steps if step["type"] == "functionBlock"]


def test_the_device_interface_report_has_a_workflow() -> None:
    named = {fb for workflow in WORKFLOWS for fb in _function_blocks(workflow)}
    assert "fb.my_worker.example.io/device_interface_report:0.2.1" in named


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_a_workflow_names_only_registered_blocks(workflow: Path) -> None:
    assert [fb for fb in _function_blocks(workflow) if fb not in registry.function_blocks] == []
