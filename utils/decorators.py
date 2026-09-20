from functools import wraps
from pyrogram.types import Message, CallbackQuery
from config import OWNER_ID


def owner_only(func):
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        user_id = None
        if isinstance(update, Message):
            user_id = update.from_user.id if update.from_user else None
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id if update.from_user else None

        if user_id != OWNER_ID:
            if isinstance(update, Message):
                await update.reply("<emoji id=5399849634350768407>❌</emoji> This command is restricted to the bot owner.")
            elif isinstance(update, CallbackQuery):
                await update.answer("❌ Owner only!", show_alert=True)
            return

        return await func(client, update, *args, **kwargs)
    return wrapper
