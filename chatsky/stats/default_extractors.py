"""
Default Extractors
------------------
This module includes a pool of default extractors
that you can use out of the box.

The default configuration for Superset dashboard leverages the data collected
by the extractors below. In order to use the default charts,
make sure that you include those functions in your pipeline.
Detailed examples can be found in the `tutorials` section.

"""

from datetime import datetime

from chatsky.script import Context
from chatsky.pipeline import ExtraHandlerRuntimeInfo, Pipeline
from .utils import get_extra_handler_name


async def get_current_label(ctx: Context, pipeline: Pipeline, info: ExtraHandlerRuntimeInfo):
    """
    Extract the current label on each turn.
    This function is required for running the dashboard with the default configuration.

    .. note::

        Preferrably, it needs to be invoked as `after_handler` of the `Actor` service.

    """
    last_label = ctx.last_label
    if last_label is None:
        last_label = pipeline.actor.start_label[:2]
    return {"flow": last_label[0], "node": last_label[1], "label": ": ".join(last_label)}


async def get_timing_before(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Store the pipeline component's start time inside the context.
    This function is required for running the dashboard with the default configuration.
    """
    start_time = datetime.now()
    ctx.framework_data.stats[get_extra_handler_name(info, "time")] = start_time


async def get_timing_after(ctx: Context, _, info: ExtraHandlerRuntimeInfo):  # noqa: F811
    """
    Extract the pipeline component's execution time.
    Requires :py:func:`~.get_timing_before` to be called previously in order to calculate the time.
    This function is required for running the dashboard with the default configuration.
    """
    start_time = ctx.framework_data.stats.pop(get_extra_handler_name(info, "time"), None)
    if start_time is None:
        return None
    data = {"execution_time": str(datetime.now() - start_time)}
    return data


async def get_last_response(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the text of the last response in the current context.
    This handler is best used together with the `ACTOR` component.

    This function is required to enable charts that aggregate requests and responses.
    """
    data = {"last_response": ctx.last_response.text}
    return data


async def get_last_request(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    """
    Extract the text of the last request in the current context.
    This handler is best used together with the `ACTOR` component.

    This function is required to enable charts that aggregate requests and responses.
    """
    data = {"last_request": ctx.last_request.text}
    return data


__all__ = ["get_current_label", "get_timing_before", "get_timing_after", "get_last_request", "get_last_response"]
"""
List of exported functions.

:meta hide-avlue:
"""
