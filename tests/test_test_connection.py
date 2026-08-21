"""Behaviour of the test_connection example function block.

Only what is honestly testable without a live device: the registration, the
no-device failure path, and the result mapping with the connection proxy
monkeypatched at the FB's import site (the SDK ships no connection mock).
The real connectivity proof is running the `simple_test_connection` workflow
against the neops-lab stack.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from neops_worker_sdk.connection.capabilities.network_device_information import InformationResult
from neops_worker_sdk.registry import registry
from neops_worker_sdk.testing.factories.context_factory import create_workflow_context
from neops_worker_sdk.workflow.workflow_context import WorkflowContext
from neops_workflow_engine_client import DeviceTypeDto

import my_worker.fb.connection_test as connection_test_module

# Aliased: bare `TestConnection*` names in this module's namespace would trip
# pytest's Test* class collector.
from my_worker.fb.connection_test import TestConnection as FbTestConnection
from my_worker.fb.connection_test import TestConnectionParameters as Params

IDENTIFIER = "fb.my_worker.example.io/test_connection:0.1.0"


def device_context() -> WorkflowContext:
    return create_workflow_context(
        run_on="device",
        entity_id=1,
        devices=[DeviceTypeDto(id=1, hostname="frr-01", ip="10.0.0.1")],
    )


def test_registration_identifier_and_run_on() -> None:
    assert IDENTIFIER in registry.function_blocks
    cls, registration, _ = registry.function_blocks[IDENTIFIER]
    assert cls is FbTestConnection
    assert registration.run_on == "device"
    assert registration.fb_type == "execute"


async def test_fails_without_device_in_context() -> None:
    result = await FbTestConnection().execute_function_block(
        params=Params(),
        context=create_workflow_context(run_on="global"),
        propagate_exceptions=True,
    )
    assert not result.success
    assert "No device found" in result.message


async def test_maps_device_information_into_result(monkeypatch: pytest.MonkeyPatch) -> None:
    info = InformationResult(
        hostname="frr-01",
        vendor="FRRouting",
        model="frr",
        serial="n/a",
        software_release="10.0",
    )

    class FakeProxy:
        @classmethod
        @contextmanager
        def connect(cls, *args: object, **kwargs: object) -> Iterator["FakeProxy"]:
            yield cls()

        def get_information(self) -> InformationResult:
            return info

    monkeypatch.setattr(connection_test_module, "NetworkDeviceDiscoveryProxy", FakeProxy)

    result = await FbTestConnection().execute_function_block(
        params=Params(),
        context=device_context(),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.hostname == "frr-01"
    assert result.data.vendor == "FRRouting"
    assert result.data.software_release == "10.0"
    assert "FRRouting 10.0" in result.message
