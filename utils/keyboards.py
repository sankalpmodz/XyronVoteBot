from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_USERNAME, OWNER_ID


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            " Add me to your channel",
            url=f"https://t.me/{BOT_USERNAME}?startchannel&admin=post_messages+edit_messages+manage_chat",
            icon_custom_emoji_id="5397916757333654639"
        )],
        [InlineKeyboardButton(" Create Giveaway", callback_data="create_giveaway", icon_custom_emoji_id="5461131730968651745")],
        [InlineKeyboardButton(" Manage Giveaways", callback_data="manage_giveaways", icon_custom_emoji_id="5341715473882955310")],
        [InlineKeyboardButton(" Manage Subscription", callback_data="manage_subscription", icon_custom_emoji_id="5332290778037235887")]
    ])


def channel_list_keyboard(channels: list, prefix: str = "select_channel"):
    buttons = []
    for ch in channels:
        display_name = ch["channel_name"] or f"Channel {ch['channel_id']}"
        buttons.append([InlineKeyboardButton(
            f" {display_name}",
            callback_data=f"{prefix}:{ch['channel_id']}",
            icon_custom_emoji_id="5424818078833715060"
        )])
    buttons.append([InlineKeyboardButton(" Back to Menu", callback_data="main_menu", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)


def confirm_giveaway_keyboard(channel_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Yes", callback_data=f"confirm_giveaway:{channel_id}", icon_custom_emoji_id="5229085643082056010")],
        [InlineKeyboardButton(" No", callback_data="cancel_giveaway", icon_custom_emoji_id="5445080884132719243")]
    ])


def giveaway_created_keyboard(giveaway_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Manage", callback_data=f"manage_ga:{giveaway_id}", icon_custom_emoji_id="5341715473882955310")],
        [InlineKeyboardButton(" Main Menu", callback_data="main_menu", icon_custom_emoji_id="5416041192905265756")]
    ])


def giveaway_channel_post_keyboard(giveaway_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            " Join Here",
            url=f"https://t.me/{BOT_USERNAME}?start={giveaway_id}",
            icon_custom_emoji_id="5330312778093704176"
        )]
    ])


def giveaway_join_keyboard(giveaway_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Join Giveaway", callback_data=f"join_giveaway:{giveaway_id}", icon_custom_emoji_id="5461151367559141950")]
    ])


def giveaway_list_keyboard(giveaways: list):
    buttons = []
    for ga in giveaways:
        display_name = ga["channel_name"] or f"Channel {ga['channel_id']}"
        buttons.append([InlineKeyboardButton(
            f" {display_name}",
            callback_data=f"manage_ga:{ga['giveaway_id']}",
            icon_custom_emoji_id="5424818078833715060"
        )])
    buttons.append([InlineKeyboardButton(" Back to Menu", callback_data="main_menu", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)


def manage_giveaway_keyboard(giveaway_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Add Votes", callback_data=f"add_votes:{giveaway_id}", icon_custom_emoji_id="5397916757333654639")],
        [InlineKeyboardButton(" Remove Votes", callback_data=f"remove_votes:{giveaway_id}", icon_custom_emoji_id="6298394017155516458")],
        [InlineKeyboardButton(" Leaderboard", callback_data=f"leaderboard:{giveaway_id}", icon_custom_emoji_id="5231200819986047254")],
        [InlineKeyboardButton(" End Giveaway", callback_data=f"end_giveaway:{giveaway_id}", icon_custom_emoji_id="5395695537687123235")],
        [InlineKeyboardButton(" AI Analyser", callback_data=f"ai_analyser:{giveaway_id}", icon_custom_emoji_id="6294154167174831283")],
        [InlineKeyboardButton(" Back", callback_data="manage_giveaways", icon_custom_emoji_id="5852498711577367193")]
    ])


def participant_list_keyboard(participants: list, giveaway_id: str, action: str):
    buttons = []
    for p in participants:
        display = p["first_name"] or p["username"] or f"User {p['user_id']}"
        buttons.append([InlineKeyboardButton(
            f" {display} (Votes: {p['votes']})",
            callback_data=f"{action}_user:{giveaway_id}:{p['user_id']}",
            icon_custom_emoji_id="6294017458365799635"
        )])
    buttons.append([InlineKeyboardButton(" Back", callback_data=f"manage_ga:{giveaway_id}", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)


def vote_button_keyboard(giveaway_id: str, user_id: int, votes: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f" Vote - {votes}",
            callback_data=f"vote:{giveaway_id}:{user_id}",
            icon_custom_emoji_id="5325547803936572038"
        )]
    ])


def subscription_keyboard(has_plan: bool, can_renew: bool = False):
    buttons = []
    if not has_plan:
        buttons.append([InlineKeyboardButton(" Buy Subscription", callback_data="buy_subscription", icon_custom_emoji_id="5226656353744862682")])
    else:
        if can_renew:
            buttons.append([InlineKeyboardButton(" Renew Plan", callback_data="renew_plan", icon_custom_emoji_id="5332290778037235887")])
        buttons.append([InlineKeyboardButton(" Upgrade / Downgrade Plan", callback_data="upgrade_downgrade_plan", icon_custom_emoji_id="5226656353744862682")])
    buttons.append([InlineKeyboardButton(" Back to Menu", callback_data="main_menu", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)


def plans_list_keyboard(plans: list):
    buttons = []
    for plan in plans:
        buttons.append([InlineKeyboardButton(
            f" {plan['name']} - {plan['price_label']} ({plan['duration_days']} days)",
            callback_data=f"buy_plan:{plan['_id']}",
            icon_custom_emoji_id="5229173741451230931"
        )])
    buttons.append([InlineKeyboardButton(" Back", callback_data="manage_subscription", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)


def buy_plan_redirect_keyboard(plan_name: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            " Contact Owner to Buy",
            url=f"https://t.me/{BOT_USERNAME}",
            icon_custom_emoji_id="5454014806950429357"
        )],
        [InlineKeyboardButton(" Back", callback_data="buy_subscription", icon_custom_emoji_id="5852498711577367193")]
    ])


def confirm_end_giveaway_keyboard(giveaway_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Yes, End It", callback_data=f"confirm_end:{giveaway_id}", icon_custom_emoji_id="6296577138615125756")],
        [InlineKeyboardButton(" No, Go Back", callback_data=f"manage_ga:{giveaway_id}", icon_custom_emoji_id="5462882007451185227")]
    ])


def back_to_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Main Menu", callback_data="main_menu", icon_custom_emoji_id="5416041192905265756")]
    ])


def create_giveaway_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(" Create Giveaway", callback_data="create_giveaway", icon_custom_emoji_id="5461151367559141950")],
        [InlineKeyboardButton(" Back to Menu", callback_data="main_menu", icon_custom_emoji_id="5852498711577367193")]
    ])


def purchase_approve_reject_keyboard(user_id: int, plan_name: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(" Approve", callback_data=f"approve_purchase:{user_id}:{plan_name}", icon_custom_emoji_id="6296577138615125756"),
            InlineKeyboardButton(" Reject", callback_data=f"reject_purchase:{user_id}", icon_custom_emoji_id="5462882007451185227")
        ]
    ])


def paginated_participant_list_keyboard(participants: list, giveaway_id: str,
                                         action: str, page: int = 0, per_page: int = 10):
    total = len(participants)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total)
    page_participants = participants[start_idx:end_idx]

    buttons = []
    for p in page_participants:
        display = p["first_name"] or p["username"] or f"User {p['user_id']}"
        buttons.append([InlineKeyboardButton(
            f" {display} (Votes: {p['votes']})",
            callback_data=f"{action}_user:{giveaway_id}:{p['user_id']}",
            icon_custom_emoji_id="6294017458365799635"
        )])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "Back",
            callback_data=f"{action}_page:{giveaway_id}:{page - 1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            "Next",
            callback_data=f"{action}_page:{giveaway_id}:{page + 1}"
        ))
    if nav_buttons:
        buttons.append(nav_buttons)

    if total_pages > 1:
        buttons.append([InlineKeyboardButton(
            f" Page {page + 1}/{total_pages}",
            callback_data="noop",
            icon_custom_emoji_id="5229121484584139947"
        )])

    buttons.append([InlineKeyboardButton(" Back", callback_data=f"manage_ga:{giveaway_id}", icon_custom_emoji_id="5852498711577367193")])
    return InlineKeyboardMarkup(buttons)
