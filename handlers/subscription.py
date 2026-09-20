import os
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
import database as db
from utils.keyboards import (
    subscription_keyboard, plans_list_keyboard, back_to_menu_keyboard
)
from utils.helpers import format_subscription_info, generate_sub_id
from config import OWNER_ID, QR_IMAGE_PATH, PURCHASE_COOLDOWN_HOURS

pending_payments = {}


def register_subscription_handlers(app: Client):

    @app.on_callback_query(filters.regex(r"^manage_subscription$"))
    async def manage_subscription_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user

        active_sub = await db.get_active_subscription(user.id)
        sub_info = await db.get_subscription_info(user.id)
        info_text = format_subscription_info(sub_info)

        has_plan = active_sub is not None
        can_renew = False
        if active_sub:
            now = datetime.datetime.utcnow()
            time_left = active_sub["expiry_date"] - now
            if time_left <= datetime.timedelta(hours=24):
                can_renew = True

        await callback_query.message.edit_text(
            info_text,
            reply_markup=subscription_keyboard(has_plan=has_plan, can_renew=can_renew)
        )

    @app.on_callback_query(filters.regex(r"^upgrade_downgrade_plan$"))
    async def upgrade_downgrade_plan_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await buy_subscription_cb(client, callback_query)

    @app.on_callback_query(filters.regex(r"^renew_plan$"))
    async def renew_plan_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user

        active_sub = await db.get_active_subscription(user.id)
        if not active_sub:
            return await buy_subscription_cb(client, callback_query)

        plan = await db.get_plan_by_name(active_sub["plan_name"])
        if not plan:
            return await buy_subscription_cb(client, callback_query)

        callback_query.data = f"buy_plan:{plan['_id']}"
        await buy_plan_cb(client, callback_query)

    @app.on_callback_query(filters.regex(r"^buy_subscription$"))
    async def buy_subscription_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user

        plans = await db.get_all_plans()
        if not plans:
            await callback_query.message.edit_text(
                "📭 <b>No Plans Available</b>\n\n"
                "There are no subscription plans available at the moment.\n"
                "Please check back later.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        has_history = await db.has_user_ever_subscribed(user.id)
        if has_history:
            plans = [p for p in plans if "trial" not in p["name"].lower()]

        if not plans:
            await callback_query.message.edit_text(
                "📭 <b>No Plans Available</b>\n\n"
                "There are no subscription plans available for you at the moment.\n"
                "Please check back later.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        text = "<emoji id=5330312778093704176>🛒</emoji> <b>Available Plans</b>\n\n"
        for plan in plans:
            text += (
                f"<emoji id=5229173741451230931>📦</emoji> <b>{plan['name']}</b>\n"
                f"   ├ Duration: {plan['duration_days']} days\n"
                f"   ├ Simultaneous Giveaways: {plan['max_giveaways']}\n"
                f"   └ Price: {plan['price_label']}\n\n"
            )
        text += "Select a plan to buy:"

        await callback_query.message.edit_text(
            text,
            reply_markup=plans_list_keyboard(plans)
        )

    @app.on_callback_query(filters.regex(r"^buy_plan:"))
    async def buy_plan_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        plan_id = callback_query.data.split(":")[1]

        from bson import ObjectId
        plan = await db.get_plan_by_id(ObjectId(plan_id))
        if not plan:
            await callback_query.answer("Plan not found!", show_alert=True)
            return

        user = callback_query.from_user

        if "trial" in plan["name"].lower():
            has_history = await db.has_user_ever_subscribed(user.id)
            if has_history:
                await callback_query.message.edit_text(
                    "❌ <b>Trial plan is not available for your account.</b>\n\n"
                    "Trial plans are only available for first-time users.",
                    reply_markup=back_to_menu_keyboard()
                )
                return

        can_request = await db.can_send_purchase_request(user.id, PURCHASE_COOLDOWN_HOURS)
        if not can_request:
            remaining = await db.get_cooldown_remaining(user.id, PURCHASE_COOLDOWN_HOURS)
            await callback_query.message.edit_text(
                f"<emoji id=5976337732710961049>⏳</emoji> <b>Cooldown Active!</b>\n\n"
                f"You have already sent a purchase request recently.\n"
                f"Please wait <b>{remaining}</b> before sending another request.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        await db.cancel_purchase_request(user.id)
        if user.id in pending_payments:
            del pending_payments[user.id]

        if not os.path.exists(QR_IMAGE_PATH):
            await callback_query.message.edit_text(
                "❌ <b>Payment QR not configured!</b>\n\n"
                "The payment QR code has not been set up yet.\n"
                "Please contact the bot owner.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        pending_payments[user.id] = {
            "plan_name": plan["name"],
            "plan_price": plan["price_label"],
            "plan_id": plan["_id"],
            "plan_duration": plan["duration_days"],
            "plan_max_giveaways": plan["max_giveaways"]
        }

        await db.create_purchase_request(user.id, plan["name"], plan["price_label"])

        await callback_query.message.delete()
        await client.send_photo(
            chat_id=user.id,
            photo=QR_IMAGE_PATH,
            caption=(
                f"<emoji id=6296218646284863141>💳</emoji> <b>Payment Required</b>\n\n"
                f"<emoji id=5251203410396458957>⚠️</emoji> <b>Plan:</b> {plan['name']}\n"
                f"<emoji id=5231005931550030290>💰</emoji> <b>Amount:</b> {plan['price_label']}\n"
                f"<emoji id=5217822164362739968>🤝</emoji> <b>Duration:</b> {plan['duration_days']} days\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<emoji id=5976544629875543840>📱</emoji> Scan the QR code above and pay <b>{plan['price_label']}</b>\n\n"
                f"After payment, <b>send the payment screenshot</b> here as a photo.\n\n"
                f"<emoji id=5447644880824181073>⚠️</emoji> <b>Important:</b> Only send a photo/screenshot. "
                f"Sending any other type of message will cancel your purchase request."
            )
        )

    @app.on_message(filters.private & filters.photo)
    async def handle_payment_screenshot(client: Client, message: Message):
        user = message.from_user

        if await db.is_user_banned(user.id):
            return

        if user.id not in pending_payments:
            return

        pending = pending_payments[user.id]

        db_pending = await db.get_pending_purchase(user.id)
        if not db_pending:
            del pending_payments[user.id]
            return

        await db.complete_purchase_request(user.id)

        del pending_payments[user.id]

        try:
            from utils.keyboards import purchase_approve_reject_keyboard
            await message.forward(chat_id=OWNER_ID)
            await client.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"<emoji id=5249037681727404734>💰</emoji> <b>New Plan Purchase Request</b>\n\n"
                    f"<b>From:</b> {user.first_name} (@{user.username or 'N/A'})\n"
                    f"<b>User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Plan:</b> {pending['plan_name']}\n"
                    f"<b>Price:</b> {pending['plan_price']}\n"
                    f"<b>Duration:</b> {pending['plan_duration']} days\n\n"
                    f"👆 Payment screenshot above"
                ),
                reply_markup=purchase_approve_reject_keyboard(user.id, pending['plan_name'])
            )
        except Exception as e:
            print(f"[ERROR] Failed to forward payment to owner: {e}")

        await message.reply(
            f"<emoji id=5391072026867802122>✅</emoji> <b>Purchase Request Sent!</b>\n\n"
            f"Your payment screenshot for the <b>{pending['plan_name']}</b> plan "
            f"has been sent to the bot owner.\n\n"
            f"You will receive a redeem code once the payment is verified.\n"
            f"Use <code>/redeem &lt;code&gt;</code> to activate your subscription.",
            reply_markup=back_to_menu_keyboard()
        )

    @app.on_message(filters.private & ~filters.photo & ~filters.command(["start", "redeem", "help",
                     "createplan", "deleteplan", "listplans", "gencode", "listcodes", "stats", "unban"]))
    async def handle_non_photo_during_payment(client: Client, message: Message):
        user = message.from_user

        if await db.is_user_banned(user.id):
            return

        if user.id not in pending_payments:
            return

        plan_name = pending_payments[user.id]["plan_name"]
        del pending_payments[user.id]
        await db.cancel_purchase_request(user.id)

        await message.reply(
            f"<emoji id=5399849634350768407>❌</emoji> <b>Purchase Request Cancelled!</b>\n\n"
            f"Your purchase request for the <b>{plan_name}</b> plan has been cancelled "
            f"because you sent a non-photo message.\n\n"
            f"Only a payment screenshot (photo) is accepted as proof of payment.",
            reply_markup=back_to_menu_keyboard()
        )

    @app.on_message(filters.command("redeem") & filters.private)
    async def redeem_command(client: Client, message: Message):
        user = message.from_user

        if await db.is_user_banned(user.id):
            return

        await db.add_user(user.id, user.username, user.first_name)

        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "<emoji id=5399849634350768407>❌</emoji> <b>Usage:</b> <code>/redeem &lt;code&gt;</code>\n\n"
                "Example: <code>/redeem ABC123XYZ456</code>"
            )
            return

        code = args[1].strip().upper()

        redeem = await db.get_redeem_code(code)
        if not redeem:
            await message.reply(
                "<emoji id=5399849634350768407>❌</emoji> <b>Invalid or Used Code!</b>\n\n"
                "This redeem code is either invalid or has already been used."
            )
            return

        plan = await db.get_plan_by_id(redeem["plan_id"])
        if not plan:
            await message.reply("<emoji id=5399849634350768407>❌</emoji> The plan associated with this code no longer exists.")
            return

        sub_id = generate_sub_id()
        await db.create_subscription(
            user_id=user.id,
            plan_name=plan["name"],
            sub_id=sub_id,
            duration_days=plan["duration_days"],
            max_giveaways=plan["max_giveaways"]
        )

        await db.use_redeem_code(code, user.id)

        sub_info = await db.get_subscription_info(user.id)
        info_text = format_subscription_info(sub_info)

        await message.reply(
            f"<emoji id=5249448542593883237>✅</emoji> <b>Subscription Activated!</b>\n\n"
            f"{info_text}\n\n"
            f"Enjoy your <b>{plan['name']}</b> plan! <emoji id=5330090758349271612>🎉</emoji>",
            reply_markup=back_to_menu_keyboard()
        )

        try:
            await client.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"<emoji id=5249448542593883237>✅</emoji> <b>Code Redeemed</b>\n\n"
                    f"<emoji id=6255512604110751681>⚠️</emoji> <b>User:</b> {user.first_name} (@{user.username or 'N/A'})\n"
                    f"<emoji id=6255512604110751681>⚠️</emoji> <b>User ID:</b> <code>{user.id}</code>\n"
                    f"<emoji id=6255512604110751681>⚠️</emoji> <b>Code:</b> <code>{code}</code>\n"
                    f"<emoji id=6255512604110751681>⚠️</emoji> <b>Plan:</b> {plan['name']}"
                )
            )
        except Exception:
            pass
