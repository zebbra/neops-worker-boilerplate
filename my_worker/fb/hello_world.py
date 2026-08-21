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
from pydantic import Field


class HelloWorldParameters(FunctionBlockParams):
    greeting: str = Field(
        title="Greeting",
        description="The greeting to use.",
        default="Hello",
        min_length=1,
    )
    name: str = Field(
        title="Name",
        description="Who to greet.",
        min_length=1,
    )


class HelloWorldResult(FunctionBlockResultData):
    message: str


@register_function_block(
    Registration(
        name="hello_world",
        description="Return a greeting. The smallest possible function block: params in, result out.",
        package="fb.my_worker.example.io",
        run_on="global",
        fb_type="execute",
        param_cls=HelloWorldParameters,
        result_cls=HelloWorldResult,
        markdown_helptext=(
            "A minimal example function block: takes a greeting and a name, returns the composed message. "
            "Touches no device and no entity — use it to verify the worker is registered and executing jobs."
        ),
        version=(0, 1, 0),
        deprecated=False,
        is_idempotent=True,
        is_pure=True,
    )
)
class HelloWorld(FunctionBlock[HelloWorldParameters, HelloWorldResult]):
    async def acquire(self, params: AcquireParams[HelloWorldParameters]) -> FunctionBlockAcquireResult:
        del params
        return FunctionBlockAcquireResult(success=True, message="No acquires required.", acquires=None)

    async def run(
        self,
        params: HelloWorldParameters,
        context: WorkflowContext,
    ) -> FunctionBlockResult[HelloWorldResult]:
        del context
        message = f"{params.greeting}, {params.name}!"
        self.logger.info(f"hello_world: {message}")
        return FunctionBlockResult(
            success=True,
            message="Greeting composed successfully.",
            data=HelloWorldResult(message=message),
        )
