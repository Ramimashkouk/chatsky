"""
Context
-------
A Context is a data structure that is used to store information about the current state of a conversation.
It is used to keep track of the user's input, the current stage of the conversation, and any other
information that is relevant to the current context of a dialog.
The Context provides a convenient interface for working with data, allowing developers to easily add,
retrieve, and manipulate data as the conversation progresses.

The Context data structure provides several key features to make working with data easier.
Developers can use the context to store any information that is relevant to the current conversation,
such as user data, session data, conversation history, or etc.
This allows developers to easily access and use this data throughout the conversation flow.

Another important feature of the context is data serialization.
The context can be easily serialized to a format that can be stored or transmitted, such as JSON.
This allows developers to save the context data and resume the conversation later.
"""

from __future__ import annotations
import logging
from uuid import UUID, uuid4
from typing import Any, Optional, Union, Dict, List, Set, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from chatsky.script.core.message import Message
from chatsky.script.core.types import NodeLabel2Type
from chatsky.pipeline.types import ComponentExecutionState
from chatsky.slots.slots import SlotManager

if TYPE_CHECKING:
    from chatsky.script.core.script import Node

logger = logging.getLogger(__name__)


def get_last_index(dictionary: dict) -> int:
    """
    Obtain the last index from the `dictionary`. Return `-1` if the `dict` is empty.

    :param dictionary: Dictionary with unsorted keys.
    :return: Last index from the `dictionary`.
    """
    indices = list(dictionary)
    return indices[-1] if indices else -1


class FrameworkData(BaseModel):
    """
    Framework uses this to store data related to any of its modules.
    """

    service_states: Dict[str, ComponentExecutionState] = Field(default_factory=dict, exclude=True)
    "Statuses of all the pipeline services. Cleared at the end of every turn."
    actor_data: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    "Actor service data. Cleared at the end of every turn."
    stats: Dict[str, Any] = Field(default_factory=dict)
    "Enables complex stats collection across multiple turns."
    slot_manager: SlotManager = Field(default_factory=SlotManager)
    "Stores extracted slots."


class Context(BaseModel):
    """
    A structure that is used to store data about the context of a dialog.

    Avoid storing unserializable data in the fields of this class in order for
    context storages to work.
    """

    id: Union[UUID, int, str] = Field(default_factory=uuid4)
    """
    `id` is the unique context identifier. By default, randomly generated using `uuid4` `id` is used.
    `id` can be used to trace the user behavior, e.g while collecting the statistical data.
    """
    labels: Dict[int, NodeLabel2Type] = Field(default_factory=dict)
    """
    `labels` stores the history of all passed `labels`

        - key - `id` of the turn.
        - value - `label` on this turn.
    """
    requests: Dict[int, Message] = Field(default_factory=dict)
    """
    `requests` stores the history of all `requests` received by the agent

        - key - `id` of the turn.
        - value - `request` on this turn.
    """
    responses: Dict[int, Message] = Field(default_factory=dict)
    """
    `responses` stores the history of all agent `responses`

        - key - `id` of the turn.
        - value - `response` on this turn.
    """
    misc: Dict[str, Any] = Field(default_factory=dict)
    """
    `misc` stores any custom data. The scripting doesn't use this dictionary by default,
    so storage of any data won't reflect on the work on the internal Chatsky Scripting functions.

    Avoid storing unserializable data in order for context storages to work.

        - key - Arbitrary data name.
        - value - Arbitrary data.
    """
    framework_data: FrameworkData = Field(default_factory=FrameworkData)
    """
    This attribute is used for storing custom data required for pipeline execution.
    It is meant to be used by the framework only. Accessing it may result in pipeline breakage.
    """

    @field_validator("labels", "requests", "responses")
    @classmethod
    def sort_dict_keys(cls, dictionary: dict) -> dict:
        """
        Sort the keys in the `dictionary`. This needs to be done after deserialization,
        since the keys are deserialized in a random order.

        :param dictionary: Dictionary with unsorted keys.
        :return: Dictionary with sorted keys.
        """
        return {key: dictionary[key] for key in sorted(dictionary)}

    @classmethod
    def cast(cls, ctx: Optional[Union[Context, dict, str]] = None, *args, **kwargs) -> Context:
        """
        Transform different data types to the objects of the
        :py:class:`~.Context` class.
        Return an object of the :py:class:`~.Context`
        type that is initialized by the input data.

        :param ctx: Data that is used to initialize an object of the
            :py:class:`~.Context` type.
            An empty :py:class:`~.Context` object is returned if no data is given.
        :return: Object of the :py:class:`~.Context`
            type that is initialized by the input data.
        """
        if not ctx:
            ctx = Context(*args, **kwargs)
        elif isinstance(ctx, dict):
            ctx = Context.model_validate(ctx)
        elif isinstance(ctx, str):
            ctx = Context.model_validate_json(ctx)
        elif not isinstance(ctx, Context):
            raise ValueError(
                f"Context expected to be an instance of the Context class "
                f"or an instance of the dict/str(json) type. Got: {type(ctx)}"
            )
        return ctx

    def add_request(self, request: Message):
        """
        Add a new `request` to the context.
        The new `request` is added with the index of `last_index + 1`.

        :param request: `request` to be added to the context.
        """
        request_message = Message.model_validate(request)
        last_index = get_last_index(self.requests)
        self.requests[last_index + 1] = request_message

    def add_response(self, response: Message):
        """
        Add a new `response` to the context.
        The new `response` is added with the index of `last_index + 1`.

        :param response: `response` to be added to the context.
        """
        response_message = Message.model_validate(response)
        last_index = get_last_index(self.responses)
        self.responses[last_index + 1] = response_message

    def add_label(self, label: NodeLabel2Type):
        """
        Add a new :py:data:`~.NodeLabel2Type` to the context.
        The new `label` is added with the index of `last_index + 1`.

        :param label: `label` that we need to add to the context.
        """
        last_index = get_last_index(self.labels)
        self.labels[last_index + 1] = label

    def clear(
        self,
        hold_last_n_indices: int,
        field_names: Union[Set[str], List[str]] = {"requests", "responses", "labels"},
    ):
        """
        Delete all records from the `requests`/`responses`/`labels` except for
        the last `hold_last_n_indices` turns.
        If `field_names` contains `misc` field, `misc` field is fully cleared.

        :param hold_last_n_indices: Number of last turns to keep.
        :param field_names: Properties of :py:class:`~.Context` to clear.
            Defaults to {"requests", "responses", "labels"}
        """
        field_names = field_names if isinstance(field_names, set) else set(field_names)
        if "requests" in field_names:
            for index in list(self.requests)[:-hold_last_n_indices]:
                del self.requests[index]
        if "responses" in field_names:
            for index in list(self.responses)[:-hold_last_n_indices]:
                del self.responses[index]
        if "misc" in field_names:
            self.misc.clear()
        if "labels" in field_names:
            for index in list(self.labels)[:-hold_last_n_indices]:
                del self.labels[index]
        if "framework_data" in field_names:
            self.framework_data = FrameworkData()

    @property
    def last_label(self) -> Optional[NodeLabel2Type]:
        """
        Return the last :py:data:`~.NodeLabel2Type` of
        the :py:class:`~.Context`.
        Return `None` if `labels` is empty.

        Since `start_label` is not added to the `labels` field,
        empty `labels` usually indicates that the current node is the `start_node`.
        """
        last_index = get_last_index(self.labels)
        return self.labels.get(last_index)

    @property
    def last_response(self) -> Optional[Message]:
        """
        Return the last `response` of the current :py:class:`~.Context`.
        Return `None` if `responses` is empty.
        """
        last_index = get_last_index(self.responses)
        return self.responses.get(last_index)

    @last_response.setter
    def last_response(self, response: Optional[Message]):
        """
        Set the last `response` of the current :py:class:`~.Context`.
        Required for use with various response wrappers.
        """
        last_index = get_last_index(self.responses)
        self.responses[last_index] = Message() if response is None else Message.model_validate(response)

    @property
    def last_request(self) -> Optional[Message]:
        """
        Return the last `request` of the current :py:class:`~.Context`.
        Return `None` if `requests` is empty.
        """
        last_index = get_last_index(self.requests)
        return self.requests.get(last_index)

    @last_request.setter
    def last_request(self, request: Optional[Message]):
        """
        Set the last `request` of the current :py:class:`~.Context`.
        Required for use with various request wrappers.
        """
        last_index = get_last_index(self.requests)
        self.requests[last_index] = Message() if request is None else Message.model_validate(request)

    @property
    def current_node(self) -> Optional[Node]:
        """
        Return current :py:class:`~chatsky.script.core.script.Node`.
        """
        actor_data = self.framework_data.actor_data
        node = (
            actor_data.get("processed_node")
            or actor_data.get("pre_response_processed_node")
            or actor_data.get("next_node")
            or actor_data.get("pre_transitions_processed_node")
            or actor_data.get("previous_node")
        )
        if node is None:
            logger.warning(
                "The `current_node` method should be called "
                "when an actor is running between the "
                "`ActorStage.GET_PREVIOUS_NODE` and `ActorStage.FINISH_TURN` stages."
            )

        return node
