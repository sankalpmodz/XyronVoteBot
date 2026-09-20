from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
import database as db
from utils.keyboards import (
    main_menu_keyboard, giveaway_join_keyboard, back_to_menu_keyboard,
    vote_button_keyboard
)
from utils.ai_analyser import analyse_user_profile
from utils.helpers import censor_text, censor_profile_field
from config import BOT_USERNAME


def register_start_handlers(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client: Client, message: Message):
        user = message.from_user

        if await db.is_user_banned(user.id):
            return

        await db.add_user(user.id, user.username, user.first_name)

        args = message.text.split()
        if len(args) > 1:
            giveaway_id = args[1].strip()
            await handle_giveaway_deeplink(client, message, giveaway_id)
            return

        await message.reply(
            f"<emoji id=5852753961483767893>👋</emoji> <b>Welcome, {user.first_name}!</b>\n\n"
            f"I'm a <b>Giveaway Voting Bot</b> for Telegram channels.\n\n"
            f"Use the buttons below to get started! <emoji id=5431784515787824439>🤝</emoji>",
            reply_markup=main_menu_keyboard()
        )

    @app.on_callback_query(filters.regex(r"^main_menu$"))
    async def main_menu_callback(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return

        await callback_query.answer()
        user = callback_query.from_user
        await callback_query.message.edit_text(
            f"<emoji id=5852753961483767893>👋</emoji> <b>Welcome, {user.first_name}!</b>\n\n"
            f"I'm a <b>Giveaway Voting Bot</b> for Telegram channels.\n\n"
            f"Use the buttons below to get started! <emoji id=5431784515787824439>🤝</emoji>",
            reply_markup=main_menu_keyboard()
        )


async def handle_giveaway_deeplink(client: Client, message: Message, giveaway_id: str):
    giveaway = await db.get_giveaway(giveaway_id)

    if not giveaway:
        await message.reply(
            "<emoji id=5210952531676504517>❌</emoji> <b>Invalid Giveaway!</b>\n\nThis giveaway link is not valid or has expired.",
            reply_markup=back_to_menu_keyboard()
        )
        return

    if giveaway["status"] != "active":
        await message.reply(
            "<emoji id=5447644880824181073>⚠️</emoji> <b>Giveaway Ended!</b>\n\nThis giveaway has already ended.",
            reply_markup=back_to_menu_keyboard()
        )
        return

    existing = await db.get_participant(giveaway_id, message.from_user.id)
    if existing:
        await message.reply(
            "<emoji id=5249448542593883237>✅</emoji> <b>Already Registered!</b>\n\nYou have already joined this giveaway.",
            reply_markup=back_to_menu_keyboard()
        )
        return

    participant_count = await db.get_participant_count(giveaway_id)
    channel_name = giveaway["channel_name"] or "Unknown Channel"

    await message.reply(
        f"<emoji id=6294287714887933094>💰</emoji> <b>Exclusive Giveaway</b>\n\n"
        f"<emoji id=5438496463044752972>👀</emoji> <b>Hosted by:</b> {channel_name}\n"
        f"<emoji id=5249281747538944392>☠️</emoji> <b>Participants:</b> {participant_count}\n\n"
        f"Click the button below to join!",
        reply_markup=giveaway_join_keyboard(giveaway_id)
    )


def register_join_handler(app: Client):

    @app.on_callback_query(filters.regex(r"^join_giveaway:"))
    async def join_giveaway_callback(client: Client, callback_query: CallbackQuery):
        user = callback_query.from_user

        if await db.is_user_banned(user.id):
            return

        try:
            await callback_query.answer()
        except Exception:
            pass
        giveaway_id = callback_query.data.split(":")[1]

        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway or giveaway["status"] != "active":
            try:
                await callback_query.message.edit_text(
                    "<emoji id=5210952531676504517>❌</emoji> This giveaway is no longer active.",
                    reply_markup=back_to_menu_keyboard()
                )
            except Exception:
                pass
            return

        existing = await db.get_participant(giveaway_id, user.id)
        if existing:
            try:
                await callback_query.message.edit_text(
                    "<emoji id=5249448542593883237>✅</emoji> <b>Already Registered!</b>\n\nYou have already joined this giveaway.",
                    reply_markup=back_to_menu_keyboard()
                )
            except Exception:
                pass
            return

        try:
            full_user = await client.get_users(user.id)
            user_bio = ""
            try:
                full_chat = await client.get_chat(user.id)
                user_bio = full_chat.bio or ""
            except Exception:
                pass

            first_name = full_user.first_name or ""
            last_name = full_user.last_name or ""
            username = full_user.username or ""

            analysis = await analyse_user_profile(
                first_name=first_name,
                last_name=last_name,
                username=username,
                bio=user_bio,
                user_id=user.id
            )

            if not analysis["safe"]:
                if not analysis.get("analysed", True):
                    try:
                        await callback_query.message.edit_text(
                            "<emoji id=5447644880824181073>⚠️</emoji> <b>Unable to process your request!</b>\n\n"
                            "<emoji id=5399849634350768407>❌</emoji> Something went wrong while processing your request.\n"
                            "<emoji id=5206607081334906820>🤝</emoji> Please try again in a few minutes.",
                            reply_markup=back_to_menu_keyboard()
                        )
                    except Exception:
                        pass
                    return

                censored_reason = censor_text(analysis['reason'])

                try:
                    await callback_query.message.edit_text(
                        "<emoji id=5445350865776941647>🚫</emoji> <b>You've been blocked!</b>\n\n"
                        "You have been blocked from this giveaway and from using this bot "
                        "due to <b>illegal/inappropriate content</b> detected in your profile.\n\n"
                        f"<emoji id=5395695537687123235>🤔</emoji> <b>Reason:</b> {censored_reason}\n\n"
                        "<emoji id=5314740656902518760>✅</emoji> If you believe this is a mistake, contact the bot owner."
                    )
                except Exception:
                    pass

                await db.ban_user(user.id, reason=analysis["reason"])

                censored_name = censor_profile_field(first_name)
                censored_last = censor_profile_field(last_name) if last_name else ""
                censored_username = censor_profile_field(username) if username else "N/A"
                censored_bio = censor_profile_field(user_bio)
                try:
                    await client.send_message(
                        chat_id=giveaway["owner_id"],
                        text=(
                            f"<emoji id=5458603043203327669>🚨</emoji> <b>Suspicious User Blocked!</b>\n\n"
                            f"<emoji id=6255512604110751681>⚠️</emoji> <b>Name:</b> {censored_name} {censored_last}\n"
                            f"<emoji id=6255512604110751681>⚠️</emoji> <b>Username:</b> {censored_username}\n"
                            f"<emoji id=6255512604110751681>⚠️</emoji> <b>User ID:</b> <code>{user.id}</code>\n"
                            f"<emoji id=6255512604110751681>⚠️</emoji> <b>Bio:</b> {censored_bio}\n\n"
                            f"<emoji id=5395695537687123235>🤔</emoji> <b>Reason:</b> {censored_reason}\n\n"
                            f"This user tried to join your giveaway in "
                            f"<b>{giveaway['channel_name']}</b> and has been "
                            f"<b>blocked</b> from the bot."
                        )
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to notify giveaway owner: {e}")

                return

        except Exception as e:
            print(f"[AI_ANALYSER] Error during profile scan: {e}")
            try:
                await callback_query.message.edit_text(
                    "<emoji id=5447644880824181073>⚠️</emoji> <b>Unable to process your request!</b>\n\n"
                    "<emoji id=5399849634350768407>❌</emoji> Something went wrong while processing your request.\n"
                    "<emoji id=5206607081334906820>🤝</emoji> Please try again in a few minutes.",
                    reply_markup=back_to_menu_keyboard()
                )
            except Exception:
                pass
            return

        await db.add_participant(
            giveaway_id=giveaway_id,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        channel_id = giveaway["channel_id"]
        display_name = user.first_name or user.username or "User"
        username_text = f"@{user.username}" if user.username else "N/A"

        try:
            channel_msg = await client.send_message(
                chat_id=channel_id,
                text=(
                    f"<emoji id=5461131730968651745>🎉</emoji> <b>New Participant Joined!</b>\n\n"
                    f"<emoji id=5852751002251300642>☠️</emoji> <b>Name:</b> {display_name}\n"
                    f"<emoji id=5852669333448167503>👀</emoji> <b>User ID:</b> <code>{user.id}</code>\n"
                    f"<emoji id=5395584242199566822>🤝</emoji> <b>Username:</b> {username_text}"
                ),
                reply_markup=vote_button_keyboard(giveaway_id, user.id, 0)
            )

            await db.update_participant_channel_message(giveaway_id, user.id, channel_msg.id)

        except Exception as e:
            print(f"[ERROR] Failed to post to channel {channel_id}: {e}")

        try:
            await callback_query.message.edit_text(
                f"<emoji id=5391072026867802122>✅</emoji> <b>Registration Successful!</b>\n\n"
                f"You have joined the giveaway in <b>{giveaway['channel_name']}</b>.\n"
                f"Share the giveaway link with your friends to get more votes!\n\n"
                f"<emoji id=5271604874419647061>💥</emoji> <code>https://t.me/{BOT_USERNAME}?start={giveaway_id}</code>",
                reply_markup=back_to_menu_keyboard()
            )
        except Exception:
            pass
