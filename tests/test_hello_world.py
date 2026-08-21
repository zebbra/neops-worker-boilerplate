"""Behaviour of the hello_world example function block (no network I/O)."""

import pytest
from neops_worker_sdk.testing.factories.context_factory import create_workflow_context
from pydantic import ValidationError

from my_worker.fb.hello_world import HelloWorld, HelloWorldParameters


async def test_hello_world_composes_greeting() -> None:
    result = await HelloWorld().execute_function_block(
        params=HelloWorldParameters(name="NeOps"),
        context=create_workflow_context(run_on="global"),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.message == "Hello, NeOps!"


async def test_hello_world_uses_custom_greeting() -> None:
    result = await HelloWorld().execute_function_block(
        params=HelloWorldParameters(greeting="Hoi", name="Zebbra"),
        context=create_workflow_context(run_on="global"),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.message == "Hoi, Zebbra!"


def test_hello_world_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        HelloWorldParameters(name="")
