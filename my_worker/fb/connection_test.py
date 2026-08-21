from neops_worker_sdk.concurrency import run_in_thread
from neops_worker_sdk.connection.capabilities.network_device_information import InformationResult
from neops_worker_sdk.connection.proxy import NetworkDeviceDiscoveryProxy
from neops_worker_sdk.function_block.acquire_params import AcquireParams
from neops_worker_sdk.function_block.function_block import (
    FunctionBlock,
    FunctionBlockAcquireResult,
    FunctionBlockParams,
    FunctionBlockResult,
    FunctionBlockResultData,
)
from neops_worker_sdk.registry.decorator import register_function_block
from neops_worker_sdk.registry.registration import Registration
from neops_worker_sdk.workflow.workflow_context import WorkflowContext

# Not named test_connection.py: the worker's FB discovery skips test_* files.
from neops_workflow_engine_client import DeviceTypeDto


class TestConnectionParameters(FunctionBlockParams):
    pass


class TestConnectionResult(FunctionBlockResultData):
    hostname: str | None
    vendor: str | None
    model: str | None
    serial: str | None
    software_release: str | None


@register_function_block(
    Registration(
        name="test_connection",
        description="Connect to the device and read basic device information, proving connectivity end to end.",
        package="fb.my_worker.example.io",
        run_on="device",
        fb_type="execute",
        param_cls=TestConnectionParameters,
        result_cls=TestConnectionResult,
        # NB: the engine stores this in a varchar(255) column — keep it short.
        markdown_helptext=(
            "Opens an SSH connection to the device via the SDK's connection proxy and reads hostname, "
            "vendor, model, serial and software release. Read-only; use it to prove worker-to-device "
            "connectivity before building real function blocks."
        ),
        version=(0, 1, 0),
        deprecated=False,
        is_idempotent=True,
        is_pure=True,
    )
)
class TestConnection(FunctionBlock[TestConnectionParameters, TestConnectionResult]):
    async def acquire(self, params: AcquireParams[TestConnectionParameters]) -> FunctionBlockAcquireResult:
        del params
        return FunctionBlockAcquireResult(success=True, message="No acquires required.", acquires=None)

    async def run(
        self,
        params: TestConnectionParameters,
        context: WorkflowContext,
    ) -> FunctionBlockResult[TestConnectionResult]:
        del params
        device = context.device
        if device is None:
            return FunctionBlockResult(
                success=False,
                message="No device found in context for TestConnection function block.",
                data=None,
            )

        # Connection failures propagate: the SDK's job wrapper turns the raised
        # exception into a failed job result with the error message.
        info = await self._read_information(device)

        message = f"Connected to {device.hostname or device.ip}: {info.vendor} {info.software_release}"
        self.logger.info(message)
        return FunctionBlockResult(
            success=True,
            message=message,
            data=TestConnectionResult(
                hostname=info.hostname,
                vendor=info.vendor,
                model=info.model,
                serial=info.serial,
                software_release=info.software_release,
            ),
        )

    @run_in_thread
    def _read_information(self, device: DeviceTypeDto) -> InformationResult:
        """Read device information over one SSH connection.

        Uses the SDK's information-only proxy (`NetworkDeviceDiscoveryProxy`,
        just the `NetworkDeviceInformationCapability`): `get_information()` is
        implemented by every platform plugin the lab uses (frr, srl), unlike
        wider capabilities such as configuration or lifecycle. Netmiko I/O is
        blocking, hence `@run_in_thread` — same pattern as the SDK's
        `global_discover_network`.
        """
        self.logger.info(f"Probing {device.ip} ({device.platform.short_name if device.platform else 'unknown'})")
        with NetworkDeviceDiscoveryProxy.connect(device, "ssh", fallback_to_default=True, logger=self.logger) as proxy:
            return proxy.get_information()
