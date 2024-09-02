import asyncio

from chatsky.core import Context, Pipeline, Message, RESPONSE, TRANSITIONS, Transition as Tr
from chatsky.core.service import ServiceGroup


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: [Tr(dst="", cnd=True)]}}}
    pipeline = Pipeline(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: [Tr(dst="", cnd=False)]}}}
    pipeline.script = new_script
    pipeline.start_label = ("new_flow", "")
    assert list(pipeline.script.keys())[0] == list(new_script.keys())[0]


def test_parallel_services():
    def interact(stage: str, run_order: list):
        async def slow_service(_: Context, __: Pipeline):
            run_order.append(stage)
            await asyncio.sleep(0)

        return slow_service

    running_order = []
    test_group = ServiceGroup(components=[
            ServiceGroup(
                name="InteractWithServiceA",
                components=[
                    interact("A1", running_order),
                    interact("A2", running_order),
                    interact("A3", running_order),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceB",
                components=[
                    interact("B1", running_order),
                    interact("B2", running_order),
                    interact("B3", running_order),
                ],
                asynchronous=True,
            ),
            ServiceGroup(
                name="InteractWithServiceC",
                components=[
                    interact("C1", running_order),
                    interact("C2", running_order),
                    interact("C3", running_order),
                ],
                asynchronous=False,
            ),
        ],
    )

    pipeline = Pipeline(script={}, start_label=("old_flow", ""))
    test_group(Context(), pipeline)
    assert running_order == ["A1", "B1", "A2", "B2", "A3", "B3", "C1", "C2", "C3"]
