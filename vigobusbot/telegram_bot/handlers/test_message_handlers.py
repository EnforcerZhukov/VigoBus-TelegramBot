"""MESSAGE HANDLERS
Telegram Bot Message Handlers for test purposes. Loaded from message_handlers.
"""

# # Native # #
import aiogram

# # Package # #
from .rate_limit_handlers.user_rate_limit_handler import handle_user_rate_limit

# # Project # #
from ..status_sender.typing_status_service import start_typing
from ...logger import *


async def command_typing_forever(message: aiogram.types.Message):
    logger.debug("Requested Test command /test_typing_forever")
    chat_id = message.chat.id
    handle_user_rate_limit(chat_id)
    await start_typing(bot=message.bot, chat_id=chat_id)


def register_handlers(dispatcher: aiogram.Dispatcher):
    """Register all the test message handlers for the given Bot Dispatcher.
    To be called from message_handlers.register_handlers only if "test" env var is True.
    """
    # Test send Typing status and never stop it (should auto-stop due to safe time limit)
    dispatcher.register_message_handler(command_typing_forever, commands=("test_typing_forever", "testTypingForever"))

    logger.debug("Registered Test Message Handlers")
