"""
Common
------
This module contains several functions which are used to run demonstrations in tutorials.
"""

from os import getenv
from typing import Tuple, Iterable
from uuid import uuid4

from chatsky.core import Message, Pipeline
from chatsky.core.message import MessageInitTypes


def is_interactive_mode() -> bool:  # pragma: no cover
    """
    Checking whether the tutorial code should be run in interactive mode.

    :return: `True` if it's being executed by Jupyter kernel and DISABLE_INTERACTIVE_MODE env variable isn't set,
        `False` otherwise.
    """

    shell = None
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
    finally:
        return shell != "ZMQInteractiveShell" and getenv("DISABLE_INTERACTIVE_MODE") is None


def check_happy_path(
    pipeline: Pipeline,
    happy_path: Iterable[Tuple[MessageInitTypes, MessageInitTypes]],
    printout: bool = False,
):
    """
    Running tutorial with provided pipeline for provided requests, comparing responses with correct expected responses.

    :param pipeline: The Pipeline instance, that will be used for checking.
    :param happy_path: A tuple of (request, response) tuples, so-called happy path,
        its requests are passed to pipeline and the pipeline responses are compared to its responses.
    :param printout: Whether to print the requests/responses during iteration.
    """
    ctx_id = uuid4()  # get random ID for current context
    for step_id, (request_raw, reference_response_raw) in enumerate(happy_path):

        request = Message.model_validate(request_raw)
        reference_response = Message.model_validate(reference_response_raw)
        if printout:
            print(f"USER: {request!r}")

        ctx = pipeline(request, ctx_id)

        actual_response = ctx.last_response
        if printout:
            print(f"BOT : {actual_response!r}")

        if reference_response != actual_response:
            raise AssertionError(
                f"""check_happy_path failed
step id: {step_id}
reference response: {reference_response}
actual response: {actual_response}
"""
            )


def run_interactive_mode(pipeline: Pipeline):  # pragma: no cover
    """
    Running tutorial with provided pipeline in interactive mode, just like with CLI messenger interface.
    The dialog won't be stored anywhere, it will only be outputted to STDOUT.

    :param pipeline: The Pipeline instance, that will be used for running.
    """

    ctx_id = uuid4()  # Random UID
    print("Start a dialogue with the bot")
    while True:
        request = input(">>> ")
        ctx = pipeline(request=Message(request), ctx_id=ctx_id)
        print(f"<<< {repr(ctx.last_response)}")
