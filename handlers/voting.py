import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ChatMemberStatus
import database as db
from utils.keyboards import vote_button_keyboard


def register_voting_handlers(app: Client):

    @app.on_callback_query(filters.regex(r"^vote:"))
    async def vote_callback(client: Client, callback_query: CallbackQuery):
        parts = callback_query.data.split(":")
        giveaway_id = parts[1]
        participant_user_id = int(parts[2])
        voter = callback_query.from_user

        if await db.is_user_banned(voter.id):
            return

        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway or giveaway["status"] != "active":
            try:
                await callback_query.answer("❌ This giveaway has ended!", show_alert=True)
            except Exception:
                pass
            return

        if voter.id == participant_user_id:
            try:
                await callback_query.answer("❌ You cannot vote for yourself!", show_alert=True)
            except Exception:
                pass
            return

        channel_id = giveaway["channel_id"]
        try:
            member = await client.get_chat_member(channel_id, voter.id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                try:
                    await callback_query.answer(
                        "❌ You must join the channel first to vote!",
                        show_alert=True
                    )
                except Exception:
                    pass
                return
        except Exception:
            try:
                await callback_query.answer(
                    "❌ You must join the channel first to vote!",
                    show_alert=True
                )
            except Exception:
                pass
            return

        has_voted = await db.has_user_voted(giveaway_id, voter.id, participant_user_id)
        if has_voted:
            try:
                await callback_query.answer(
                    "❌ You have already voted for this participant!",
                    show_alert=True
                )
            except Exception:
                pass
            return

        await db.update_participant_votes(giveaway_id, participant_user_id, 1)
        await db.add_vote_log(giveaway_id, voter.id, participant_user_id, "public", 1)

        participant = await db.get_participant(giveaway_id, participant_user_id)
        new_votes = participant["votes"] if participant else 1

        try:
            await callback_query.answer(f"✅ Vote added! Total: {new_votes}", show_alert=False)
        except Exception:
            pass

        try:
            await callback_query.message.edit_reply_markup(
                reply_markup=vote_button_keyboard(giveaway_id, participant_user_id, new_votes)
            )
        except Exception as e:
            print(f"[ERROR] Failed to update vote button: {e}")
