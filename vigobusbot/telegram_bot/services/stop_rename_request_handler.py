"""STOP RENAME REQUEST HANDLER
Handler and utils for working with Stop Rename requests, involving Force Reply handling
"""

# # Native # #
import re
import contextlib
from typing import Optional

# # Installed # #
import aiogram
import cachetools
import emoji

# # Project # #
from vigobusbot.telegram_bot.services.message_generators import generate_stop_message, SourceContext
from vigobusbot.vigobus_api import get_stop
from vigobusbot.persistence_api.saved_stops import save_stop
from vigobusbot.static_handler import get_messages
from vigobusbot.settings_handler import telegram_settings as settings
from vigobusbot.logger import logger

__all__ = (
    "StopRenameRequestContext",
    "register_stop_rename_request", "handle_stop_rename_request_reply", "get_stop_rename_request_context"
)

_stop_rename_requests = cachetools.TTLCache(maxsize=float("inf"), ttl=settings.force_reply_ttl)
"""Storage for Stop Rename requests, which must be replied by users in less than the force_reply_ttl
Key=force_reply_message_id
Value=StopRenameRequestContext
"""


class StopRenameRequestContext(SourceContext):
    force_reply_message_id: int


def register_stop_rename_request(context: StopRenameRequestContext):
    """Register a Stop rename request on the _stop_rename_requests local cache.
    The key is the Message ID of the Force Reply message sent by the bot.and
    The value is the StopRenameRequestContext object.
    """
    force_reply_message_id = context.force_reply_message_id
    _stop_rename_requests[force_reply_message_id] = context
    logger.bind(force_reply_message_id=force_reply_message_id).debug("Registered Stop Rename Request for message")


def get_stop_rename_request_context(
        force_reply_message_id: Optional[int] = None, user_id: Optional[int] = None, pop: bool = True
) -> Optional[StopRenameRequestContext]:
    """Search the Context of a Stop Rename request, given the Message ID of the Force Reply message sent by the bot,
    OR the User ID that requested it - In this last case the context is searched on the local cache,
    supposing only one request exists per user, since the first result is acquired; if not found, return None.
    """
    result: Optional[StopRenameRequestContext] = None

    if user_id and not force_reply_message_id:
        with contextlib.suppress(StopIteration):
            force_reply_message_id = next(
                force_reply_message_id
                for force_reply_message_id, context
                in _stop_rename_requests.items()
                if context.user_id == user_id
            )

    if force_reply_message_id:
        with contextlib.suppress(KeyError):
            if pop:
                result = _stop_rename_requests.pop(force_reply_message_id)
            else:
                result = _stop_rename_requests[force_reply_message_id]

    logger.bind(
        force_reply_message_id=force_reply_message_id,
        with_user_id=bool(user_id),
        pop_result=pop
    ).debug(f"{'Found' if result else 'Not Found'} StopRenameRequestContext")
    return result


async def handle_stop_rename_request_reply(user_reply_message: aiogram.types.Message, remove_custom_name=False):
    """This handler is called from message handlers when a user replies to a Stop Rename ForceReply request.
    The user can reply with a custom name, or requesting to remove the already existing custom stop name.
    If setting a custom name, user_reply_message is the message sent by the user with the desired custom name.
    If removing a custom name, remove_custom_name=True and user_reply_message is the command message sent by the user.
    """
    new_stop_name = user_reply_message.text
    chat_id = user_reply_message.chat.id
    messages = get_messages()
    logger.bind(
        user_reply_message_id=user_reply_message.message_id
    ).debug("Processing Stop Rename request from reply message")

    if remove_custom_name:
        new_stop_name = None
        rename_context = get_stop_rename_request_context(user_id=user_reply_message.from_user.id)
    else:
        new_stop_name = emoji.demojize(new_stop_name)
        new_stop_name = re.sub(
            pattern=messages.stop_rename.regex_sub,
            repl='',
            string=new_stop_name
        )
        new_stop_name = emoji.emojize(new_stop_name)
        rename_context = get_stop_rename_request_context(user_reply_message.reply_to_message.message_id)

    await save_stop(
        user_id=chat_id,
        stop_id=rename_context.stop_id,
        stop_name=new_stop_name
    )

    # Getting the Stop info is required as part of message text sent to user confirming that stop got renamed
    stop = await get_stop(rename_context.stop_id)

    if not remove_custom_name:
        text = messages.stop_rename.renamed_successfully.format(
            stop_id=stop.stop_id,
            stop_name=stop.name,
            custom_stop_name=new_stop_name
        )
    else:
        text = messages.stop_rename.unnamed_successfully.format(
            stop_id=stop.stop_id,
            stop_name=stop.name
        )

    await user_reply_message.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=user_reply_message.message_id
    )
    # Remove ForceReply message sent by bot to avoid client from getting asked for a reply when reopening the client
    await user_reply_message.bot.delete_message(
        chat_id=chat_id,
        message_id=rename_context.force_reply_message_id
    )

    # Edit original Stop message
    logger.debug("Stop successfully renamed. Editing the original Stop message after renaming the Stop")
    source_context = SourceContext(
        stop_id=rename_context.stop_id,
        user_id=chat_id,
        source_message=rename_context.source_message
    )
    text, buttons = await generate_stop_message(context=source_context)
    await user_reply_message.bot.edit_message_text(
        chat_id=chat_id,
        text=text,
        message_id=rename_context.source_message.message_id,
        reply_markup=buttons
    )
    logger.debug("Edited the original Stop message after renaming the Stop")
