"""Behaviour of the device_interface_report example function block (no network I/O)."""

import pytest
from neops_worker_sdk.function_block.acquire_params import AcquireParams
from neops_worker_sdk.testing.factories.context_factory import create_workflow_context
from neops_worker_sdk.testing.factories.job_meta_factory import create_job_meta
from neops_worker_sdk.workflow import EntityType
from neops_worker_sdk.workflow.workflow_context import WorkflowContext
from neops_workflow_engine_client import DeviceTypeDto, InterfaceStateEnum, InterfaceTypeDto, JobType
from pydantic import ValidationError

from my_worker.fb.device_interface_report import (
    DeviceInterfaceReport,
    DeviceInterfaceReportParameters,
)


def device_context() -> WorkflowContext:
    return create_workflow_context(
        run_on="device",
        entity_id=1,
        devices=[DeviceTypeDto(id=1, hostname="rtr-01", ip="10.0.0.1")],
        interfaces=[
            InterfaceTypeDto(id=1, name="eth0", state=InterfaceStateEnum.UP),
            InterfaceTypeDto(id=2, name="eth1", state=InterfaceStateEnum.DOWN),
            InterfaceTypeDto(id=3, name="eth2", state=InterfaceStateEnum.UP),
        ],
    )


async def test_report_counts_all_interfaces() -> None:
    result = await DeviceInterfaceReport().execute_function_block(
        params=DeviceInterfaceReportParameters(),
        context=device_context(),
        meta=create_job_meta(),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.hostname == "rtr-01"
    assert result.data.interface_count == 3
    assert result.data.interface_names == ["eth0", "eth1", "eth2"]


async def test_report_filters_by_state() -> None:
    result = await DeviceInterfaceReport().execute_function_block(
        params=DeviceInterfaceReportParameters(state_filter=InterfaceStateEnum.UP),
        context=device_context(),
        meta=create_job_meta(),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.interface_count == 2
    assert result.data.interface_names == ["eth0", "eth2"]


async def test_report_caps_listed_names() -> None:
    result = await DeviceInterfaceReport().execute_function_block(
        params=DeviceInterfaceReportParameters(max_names=1),
        context=device_context(),
        meta=create_job_meta(),
        propagate_exceptions=True,
    )
    assert result.success
    assert result.data is not None
    assert result.data.interface_count == 3
    assert result.data.interface_names == ["eth0"]


async def test_acquire_requests_interfaces() -> None:
    params = AcquireParams(
        partial=DeviceInterfaceReportParameters(),
        unresolved=frozenset(),
        raw={},
    )
    acquire_result = await DeviceInterfaceReport().acquire(params, create_job_meta(job_type=JobType.ACQUIRE))
    assert acquire_result.success
    assert acquire_result.acquires is not None
    assert len(acquire_result.acquires) == 1
    assert acquire_result.acquires[0].entity == EntityType.INTERFACE


def test_report_rejects_an_unknown_state_filter() -> None:
    with pytest.raises(ValidationError):
        DeviceInterfaceReportParameters.model_validate({"state_filter": "up"})


def test_report_rejects_out_of_range_max_names() -> None:
    # model_validate: a literal `max_names=0` would (rightly) already fail the
    # static type check against the Field's `ge=1` constraint — this test is
    # about the runtime validation an engine payload goes through.
    with pytest.raises(ValidationError):
        DeviceInterfaceReportParameters.model_validate({"max_names": 0})
