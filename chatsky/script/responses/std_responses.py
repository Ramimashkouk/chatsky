"""
Responses
---------
Responses determine the response that will be sent to the user for each node of the dialog graph.
Responses are used to provide the user with information, ask questions,
or guide the conversation in a particular direction.

This module provides only one predefined response function that can be used to quickly
respond to the user and keep the conversation flowing.
"""

import random
from typing import List

from chatsky.pipeline import Pipeline
from chatsky.script import Context, Message


def choice(*responses):
    """
    Function wrapper that takes the list of responses as an input
    and returns handler which outputs a response randomly chosen from that list.

    :param responses: A list of responses for random sampling.
    """

    def choice_response_handler(ctx: Context, pipeline: Pipeline):
        return random.choice(responses)

    return choice_response_handler
