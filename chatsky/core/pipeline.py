"""
Pipeline
--------
The Pipeline module contains the :py:class:`.Pipeline` class,
which is a fundamental element of Chatsky. The Pipeline class is responsible
for managing and executing the various components (:py:class:`.PipelineComponent`)which make up
the processing of messages from and to users.
It provides a way to organize and structure the messages processing flow.
The Pipeline class is designed to be highly customizable and configurable,
allowing developers to add, remove, or modify the components that make up the messages processing flow.

The Pipeline class is designed to be used in conjunction with the :py:class:`.PipelineComponent`
class, which is defined in the Component module. Together, these classes provide a powerful and flexible way
to structure and manage the messages processing flow.
"""

import asyncio
import logging
from functools import cached_property
from typing import Union, List, Dict, Optional, Hashable
from pydantic import BaseModel, Field, model_validator, computed_field

from chatsky.context_storages import DBContextStorage
from chatsky.core.script import Script
from chatsky.core.context import Context
from chatsky.core.message import Message

from chatsky.messengers.console import CLIMessengerInterface
from chatsky.messengers.common import MessengerInterface
from chatsky.slots.slots import GroupSlot
from chatsky.core.service.group import ServiceGroup
from chatsky.core.service.extra import ComponentExtraHandler
from chatsky.core.service.types import (
    GlobalExtraHandlerType,
    ExtraHandlerFunction,
)
from .utils import finalize_service_group
from chatsky.core.service.actor import Actor
from chatsky.core.node_label import AbsoluteNodeLabel

logger = logging.getLogger(__name__)


class Pipeline(BaseModel, extra="forbid", arbitrary_types_allowed=True):
    """
    Class that automates service execution and creates service pipeline.
    It accepts constructor parameters:
    """

    pre_services: ServiceGroup = Field(default_factory=list)
    """
    List of :py:class:`~.Service` or :py:class:`~.ServiceGroup`
    that will be executed before Actor.
    """
    post_services: ServiceGroup = Field(default_factory=list)
    """
    List of :py:class:`~.Service` or :py:class:`~.ServiceGroup` that will be
    executed after :py:class:`~.Actor`. It constructs root
    service group by merging `pre_services` + actor + `post_services`. It will always be named pipeline.
    """
    script: Script
    """
    (required) A :py:class:`~.Script` instance (object or dict).
    """
    start_label: AbsoluteNodeLabel
    """
    (required) :py:class:`~.Actor` start label.
    """
    fallback_label: Optional[AbsoluteNodeLabel] = None
    """
    :py:class:`~.Actor` fallback label.
    """
    default_priority: float = 1.0
    """
    Default priority value for all actor :py:const:`labels <chatsky.script.ConstLabel>`
    where there is no priority. Defaults to `1.0`.
    """
    slots: GroupSlot = Field(default_factory=GroupSlot)
    """
    Slots configuration.
    """
    messenger_interface: MessengerInterface = Field(default_factory=CLIMessengerInterface)
    """
    An `AbsMessagingInterface` instance for this pipeline.
    """
    context_storage: Union[DBContextStorage, Dict] = Field(default_factory=dict)
    """
    A :py:class:`~.DBContextStorage` instance for this pipeline or
    a dict to store dialog :py:class:`~.Context`.
    """
    before_handler: ComponentExtraHandler = Field(default_factory=list)
    """
    List of :py:class:`~._ComponentExtraHandler` to add to the group.
    """
    after_handler: ComponentExtraHandler = Field(default_factory=list)
    """
    List of :py:class:`~._ComponentExtraHandler` to add to the group.
    """
    timeout: Optional[float] = None
    """
    Timeout to add to pipeline root service group.
    """
    optimization_warnings: bool = False
    """
    Asynchronous pipeline optimization check request flag;
    warnings will be sent to logs. Additionally, it has some calculated fields:

    - `_services_pipeline` is a pipeline root :py:class:`~.ServiceGroup` object,
    - `actor` is a pipeline actor, found among services.

    """
    parallelize_processing: bool = False
    """
    This flag determines whether or not the functions
    defined in the ``PRE_RESPONSE_PROCESSING`` and ``PRE_TRANSITIONS_PROCESSING`` sections
    of the script should be parallelized over respective groups.
    """

    @computed_field
    @cached_property
    def actor(self) -> Actor:
        return Actor(
            script=self.script,
            fallback_label=self.fallback_label or self.start_label,
            default_priority=self.default_priority,
        )

    @computed_field
    @cached_property
    def _services_pipeline(self) -> ServiceGroup:
        components = [self.pre_services, self.actor, self.post_services]
        services_pipeline = ServiceGroup(
            components=components,
            before_handler=self.before_handler,
            after_handler=self.after_handler,
            timeout=self.timeout,
        )
        services_pipeline.name = "pipeline"
        services_pipeline.path = ".pipeline"
        return services_pipeline

    @model_validator(mode="after")
    def validate_start_label(self):
        if self.script.get_node(self.start_label) is None:
            raise ValueError(f"Unknown start_label={self.start_label}")
        return self

    @model_validator(mode="after")
    def validate_fallback_label(self):
        if self.fallback_label is None:
            self.fallback_label = self.start_label
        if self.script.get_node(self.fallback_label) is None:
            raise ValueError(f"Unknown fallback_label={self.fallback_label}")
        return self

    @model_validator(mode="after")
    def __pipeline_init__(self):
        finalize_service_group(self._services_pipeline, path=self._services_pipeline.path)

        if self.optimization_warnings:
            self._services_pipeline.log_optimization_warnings()

        return self

    def add_global_handler(
        self,
        global_handler_type: GlobalExtraHandlerType,
        extra_handler: ExtraHandlerFunction,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ):
        """
        Method for adding global wrappers to pipeline.
        Different types of global wrappers are called before/after pipeline execution
        or before/after each pipeline component.
        They can be used for pipeline statistics collection or other functionality extensions.
        NB! Global wrappers are still wrappers,
        they shouldn't be used for much time-consuming tasks (see ../service/wrapper.py).

        :param global_handler_type: (required) indication where the wrapper
            function should be executed.
        :param extra_handler: (required) wrapper function itself.
        :type extra_handler: ExtraHandlerFunction
        :param whitelist: a list of services to only add this wrapper to.
        :param blacklist: a list of services to not add this wrapper to.
        :return: `None`
        """

        def condition(name: str) -> bool:
            return (whitelist is None or name in whitelist) and (blacklist is None or name not in blacklist)

        if (
            global_handler_type is GlobalExtraHandlerType.BEFORE_ALL
            or global_handler_type is GlobalExtraHandlerType.AFTER_ALL
        ):
            whitelist = ["pipeline"]
            global_handler_type = (
                GlobalExtraHandlerType.BEFORE
                if global_handler_type is GlobalExtraHandlerType.BEFORE_ALL
                else GlobalExtraHandlerType.AFTER
            )

        self._services_pipeline.add_extra_handler(global_handler_type, extra_handler, condition)

    @property
    def info_dict(self) -> dict:
        """
        Property for retrieving info dictionary about this pipeline.
        Returns info dict, containing most important component public fields as well as its type.
        All complex or unserializable fields here are replaced with 'Instance of [type]'.
        """
        return {
            "type": type(self).__name__,
            "messenger_interface": f"Instance of {type(self.messenger_interface).__name__}",
            "context_storage": f"Instance of {type(self.context_storage).__name__}",
            "services": [self._services_pipeline.info_dict],
        }

    async def _run_pipeline(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        if ctx_id is None:
            ctx = Context.init(self.start_label)
        elif isinstance(self.context_storage, DBContextStorage):
            ctx = await self.context_storage.get_async(ctx_id, Context.init(self.start_label, id=ctx_id))
        else:
            ctx = self.context_storage.get(ctx_id, Context.init(self.start_label, id=ctx_id))

        if update_ctx_misc is not None:
            ctx.misc.update(update_ctx_misc)

        if self.slots is not None:
            ctx.framework_data.slot_manager.set_root_slot(self.slots)

        ctx.framework_data.pipeline = self

        ctx.add_request(request)
        result = await self._services_pipeline(ctx, self)

        if asyncio.iscoroutine(result):
            await result

        ctx.framework_data.service_states.clear()
        ctx.framework_data.pipeline = None

        if isinstance(self.context_storage, DBContextStorage):
            await self.context_storage.set_item_async(ctx_id, ctx)
        else:
            self.context_storage[ctx_id] = ctx

        return ctx

    def run(self):
        """
        Method that starts a pipeline and connects to `messenger_interface`.
        It passes `_run_pipeline` to `messenger_interface` as a callbacks,
        so every time user request is received, `_run_pipeline` will be called.
        This method can be both blocking and non-blocking. It depends on current `messenger_interface` nature.
        Message interfaces that run in a loop block current thread.
        """
        asyncio.run(self.messenger_interface.connect(self._run_pipeline))

    def __call__(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that executes pipeline once.
        Basically, it is a shortcut for `_run_pipeline`.
        NB! When pipeline is executed this way, `messenger_interface` won't be initiated nor connected.

        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        return asyncio.run(self._run_pipeline(request, ctx_id, update_ctx_misc))

    @property
    def script(self) -> Script:
        return self.actor.script
