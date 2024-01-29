# %% [markdown]
"""
# Telegram: 5. Conditions with Media

This tutorial shows how to use media-related logic in your script.

Here, %mddoclink(api,messengers.telegram.messenger,telegram_condition)
function is used for graph navigation according to Telegram events.

Different %mddoclink(api,script.core.message,message)
classes are used for representing different common message features,
like Attachment, Audio, Button, Image, etc.
"""


# %pip install dff[telegram]

# %%
import os
from typing import cast

from pydantic import HttpUrl
from telegram import Update, Message as TelegramMessage

import dff.script.conditions as cnd
from dff.script import Context, TRANSITIONS, RESPONSE
from dff.script.core.message import Message, Image
from dff.messengers.telegram import PollingTelegramInterface, telegram_condition
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %%

picture_url = HttpUrl("https://avatars.githubusercontent.com/u/29918795?s=200&v=4")


# %% [markdown]
"""
To filter user messages depending on whether or not media files were sent,
you can use the `content_types` parameter of the `telegram_condition`.
"""


# %%
interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("pics", "ask_picture"): cnd.any(
                    [
                        cnd.exact_match(Message(text="start")),
                        cnd.exact_match(Message(text="restart")),
                    ]
                )
            },
        },
        "fallback": {
            RESPONSE: Message(
                text="Finishing test, send /restart command to restart"
            ),
            TRANSITIONS: {
                ("pics", "ask_picture"): cnd.any(
                    [
                        cnd.exact_match(Message(text="start")),
                        cnd.exact_match(Message(text="restart")),
                    ]
                )
            },
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Message(text="Send me a picture"),
            TRANSITIONS: {
                ("pics", "send_one"): cnd.any(
                    [
                        # Telegram can put photos
                        # both in 'photo' and 'document' fields.
                        # We should consider both cases
                        # when we check the message for media.
                        telegram_condition(
                            func=lambda update: (
                                update.message is not None
                                and len(update.message.photo) > 0
                            )
                        ),
                        telegram_condition(
                            func=lambda update: (
                                # check attachments in message properties
                                update.message is not None
                                and update.message.document is not None
                                and update.message.document.mime_type == "image/jpeg"
                            )
                        ),
                    ]
                ),
                ("pics", "send_many"): telegram_condition(
                    func=lambda upd: upd.message is not None and upd.message.text is not None
                ),
                ("pics", "ask_picture"): cnd.true(),
            },
        },
        "send_one": {
            # An HTTP path or a path to a local file can be used here.
            RESPONSE: Message(
                text="Here's my picture!",
                attachments=[Image(source=picture_url)],
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Message(
                text="Look at my pictures!",
                # An HTTP path or a path to a local file can be used here.
                attachments=list(tuple([Image(source=picture_url)] * 2)),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


# testing
happy_path = (
    (
        Message(text="/start"),
        Message(text="Send me a picture"),
    ),
    (
        Message(
            attachments=[Image(source=picture_url)]
        ),
        Message(
            text="Here's my picture!",
            attachments=[Image(source=picture_url)],
        ),
    ),
    (
        Message(text="ok"),
        Message(
            text="Finishing test, send /restart command to restart"
        ),
    ),
    (
        Message(text="/restart"),
        Message(text="Send me a picture"),
    ),
    (
        Message(text="No"),
        Message(
            text="Look at my pictures!",
            attachments=list(tuple([Image(source=picture_url)] * 2)),
        ),
    ),
    (
        Message(text="ok"),
        Message(
            text="Finishing test, send /restart command to restart"
        ),
    ),
    (
        Message(text="/restart"),
        Message(text="Send me a picture"),
    ),
)


# %%
async def extract_data(ctx: Context, _: Pipeline):  # A function to extract data with
    message = ctx.last_request
    if message is None:
        return
    original_update = cast(Update, message.original_message)
    if original_update is None:
        return
    if not isinstance(original_update, Update):
        return
    original_message = original_update.message
    if not isinstance(original_message, TelegramMessage):
        return
    if original_message is None:
        return
    if (
        # check attachments in update properties
        len(original_message.photo) > 0
        and not (original_message.document is not None and original_message.document.mime_type == "image/jpeg")
    ):
        return
    photo = original_message.document or original_message.photo[-1]
    await (await photo.get_file()).download_to_drive("photo.jpg")
    return


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
    pre_services=[extract_data],
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
