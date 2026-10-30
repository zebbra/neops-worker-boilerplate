from neops_worker_sdk.function_block.acquire_params import AcquireParams
from neops_worker_sdk.function_block.function_block import (
    DeviceFunctionBlock,
    FunctionBlockAcquireResult,
    FunctionBlockParams,
    FunctionBlockResult,
    FunctionBlockResultData,
)
from neops_worker_sdk.function_block.job_meta import JobMeta
from neops_worker_sdk.registry.decorator import register_function_block
from neops_worker_sdk.registry.registration import Registration
from neops_worker_sdk.workflow import EntityType
from neops_worker_sdk.workflow.workflow_context import DeviceWorkflowContext
from neops_workflow_engine_client import EntityAcquireByElasticQuery, InterfaceStateEnum
from pydantic import Field


class DeviceInterfaceReportParameters(FunctionBlockParams):
    state_filter: InterfaceStateEnum | None = Field(
        title="State filter",
        description="Only count interfaces in this state. Counts every interface when unset.",
        default=None,
    )
    max_names: int = Field(
        title="Maximum names",
        description="Cap on how many interface names to list in the result.",
        default=25,
        ge=1,
        le=1000,
    )


class DeviceInterfaceReportResult(FunctionBlockResultData):
    hostname: str
    interface_count: int
    interface_names: list[str]


@register_function_block(
    Registration(
        name="device_interface_report",
        description="Summarise a device's interfaces from the workflow context. No device connection.",
        package="fb.my_worker.example.io",
        fb_type="execute",
        param_cls=DeviceInterfaceReportParameters,
        result_cls=DeviceInterfaceReportResult,
        # NB: the engine stores this in a varchar(255) column — keep it short.
        markdown_helptext=(
            "Example FB: counts and lists the device's interfaces from the workflow context, optionally "
            "filtered by state; no device connection. Caveat: its acquire() query is a placeholder pinned "
            "to device.id 1 — see the comment in the source."
        ),
        version=(0, 2, 0),
        deprecated=False,
        is_idempotent=True,
        is_pure=True,
    )
)
class DeviceInterfaceReport(DeviceFunctionBlock[DeviceInterfaceReportParameters, DeviceInterfaceReportResult]):
    async def acquire(
        self, params: AcquireParams[DeviceInterfaceReportParameters], meta: JobMeta
    ) -> FunctionBlockAcquireResult:
        # Parameters fed from earlier steps' results are not resolved at ACQUIRE
        # time (see AcquireParams); this block only needs the step's entity, so
        # no branching on `params.unresolved` is required here.
        del params, meta
        acquires = [
            EntityAcquireByElasticQuery(
                type="elastic",
                entity=EntityType.INTERFACE,
                # ⚠️ Known-limited placeholder, mirrored from the SDK's own
                # base FBs: this acquires the interfaces of device id 1
                # regardless of which device the FB actually runs on. The
                # limitation is tracked in the SDK at
                # neops/fb/base/network_device/get_interfaces.py (see the
                # commented-out acquires and TODOs there). Replace the query
                # with one that fits your data model before copying this
                # pattern into a production FB.
                query="device.id: 1",
                assertNotEmpty=False,
                description="Acquire the interfaces of the device being reported on.",
            )
        ]
        return FunctionBlockAcquireResult(
            success=True,
            message="Acquiring the device's interfaces.",
            acquires=acquires,
        )

    async def run(
        self,
        params: DeviceInterfaceReportParameters,
        context: DeviceWorkflowContext,
        meta: JobMeta,
    ) -> FunctionBlockResult[DeviceInterfaceReportResult]:
        del meta
        device = context.device
        self.logger.debug("Running DeviceInterfaceReport on device: {}", device.hostname)

        interfaces = context.interfaces if context.interfaces is not None else []
        matching = [
            interface
            for interface in interfaces
            if params.state_filter is None or interface.state == params.state_filter
        ]
        names = [interface.name for interface in matching if interface.name is not None]

        return FunctionBlockResult(
            success=True,
            message=f"Found {len(matching)} interface(s) on {device.hostname}.",
            data=DeviceInterfaceReportResult(
                hostname=device.hostname or "",
                interface_count=len(matching),
                interface_names=names[: params.max_names],
            ),
        )
