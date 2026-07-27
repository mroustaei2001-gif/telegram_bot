import os
import json
import logging
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not all([BOT_TOKEN, ADMIN_ID]):
    raise ValueError("BOT_TOKEN and ADMIN_ID must be set in environment variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== فایل‌های ذخیره‌سازی ==========
TOPIC_FILE = "daily_topic.txt"
SENT_USERS_FILE = "sent_users.json"
SETTINGS_FILE = "settings.json"
PROXIES_FILE = "proxies.json"
PROXY_ACCESS_FILE = "proxy_access.json"
REFERRALS_FILE = "referrals.json"

def save_topic(topic):
    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        f.write(topic)

def load_topic():
    try:
        with open(TOPIC_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "موضوعی ثبت نشده"

def load_sent_users():
    try:
        with open(SENT_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_sent_users(users):
    with open(SENT_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)

def clear_sent_users():
    save_sent_users([])

def has_user_sent(user_id):
    users = load_sent_users()
    return str(user_id) in users

def add_user_to_sent(user_id):
    users = load_sent_users()
    users.append(str(user_id))
    save_sent_users(users)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "force_join": True,
            "promo_channels": [],
            "show_promo": True,
            "channel_id": os.getenv("CHANNEL_ID", ""),
            "channel_link": os.getenv("CHANNEL_LINK", ""),
            "required_referrals": 2,
            "proxy_enabled": True
        }

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_channel_id():
    settings = load_settings()
    return settings.get("channel_id", os.getenv("CHANNEL_ID", ""))

def get_channel_link():
    settings = load_settings()
    return settings.get("channel_link", os.getenv("CHANNEL_LINK", ""))

def set_channel(channel_id, channel_link):
    settings = load_settings()
    settings["channel_id"] = channel_id
    settings["channel_link"] = channel_link
    save_settings(settings)

def is_force_join_enabled():
    settings = load_settings()
    return settings.get("force_join", True)

def toggle_force_join():
    settings = load_settings()
    current = settings.get("force_join", True)
    settings["force_join"] = not current
    save_settings(settings)
    return not current

def get_promo_channels():
    settings = load_settings()
    return settings.get("promo_channels", [])

def add_promo_channel(name, link):
    settings = load_settings()
    if "promo_channels" not in settings:
        settings["promo_channels"] = []
    settings["promo_channels"].append({"name": name, "link": link})
    save_settings(settings)

def remove_promo_channel(index):
    settings = load_settings()
    if "promo_channels" in settings and 0 <= index < len(settings["promo_channels"]):
        settings["promo_channels"].pop(index)
        save_settings(settings)
        return True
    return False

def is_promo_enabled():
    settings = load_settings()
    return settings.get("show_promo", True)

def toggle_promo():
    settings = load_settings()
    current = settings.get("show_promo", True)
    settings["show_promo"] = not current
    save_settings(settings)
    return not current

def get_required_referrals():
    settings = load_settings()
    return settings.get("required_referrals", 2)

def set_required_referrals(count):
    settings = load_settings()
    settings["required_referrals"] = count
    save_settings(settings)

def is_proxy_enabled():
    settings = load_settings()
    return settings.get("proxy_enabled", True)

def toggle_proxy():
    settings = load_settings()
    current = settings.get("proxy_enabled", True)
    settings["proxy_enabled"] = not current
    save_settings(settings)
    return not current

# ========== توابع مدیریت پروکسی ==========
def load_proxies():
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_proxies(proxies):
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        json.dump(proxies, f, ensure_ascii=False, indent=2)

def add_proxy(proxy_string):
    proxies = load_proxies()
    proxies.append(proxy_string)
    save_proxies(proxies)

def remove_proxy(index):
    proxies = load_proxies()
    if 0 <= index < len(proxies):
        proxies.pop(index)
        save_proxies(proxies)
        return True
    return False

# ========== توابع دسترسی پروکسی ==========
def load_proxy_access():
    try:
        with open(PROXY_ACCESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_proxy_access(access_data):
    with open(PROXY_ACCESS_FILE, "w", encoding="utf-8") as f:
        json.dump(access_data, f, ensure_ascii=False, indent=2)

def can_user_access_proxy(user_id):
    access_data = load_proxy_access()
    user_key = str(user_id)
    if user_key not in access_data:
        return True, None
    
    last_access = datetime.fromisoformat(access_data[user_key]["last_access"])
    if datetime.now() - last_access < timedelta(days=1):
        return False, last_access
    return True, None

def record_proxy_access(user_id, bonus=False):
    access_data = load_proxy_access()
    user_key = str(user_id)
    access_data[user_key] = {
        "last_access": datetime.now().isoformat(),
        "bonus_used": bonus
    }
    save_proxy_access(access_data)

# ========== توابع سیستم دعوت ==========
def load_referrals():
    try:
        with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_referrals(referrals):
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        json.dump(referrals, f, ensure_ascii=False, indent=2)

def add_referral(referrer_id, referred_id):
    referrals = load_referrals()
    referrer_key = str(referrer_id)
    if referrer_key not in referrals:
        referrals[referrer_key] = []
    if str(referred_id) not in referrals[referrer_key]:
        referrals[referrer_key].append(str(referred_id))
        save_referrals(referrals)
        return True
    return False

def get_referral_count(user_id):
    referrals = load_referrals()
    return len(referrals.get(str(user_id), []))

def get_referrer_id(referred_id):
    referrals = load_referrals()
    for referrer, referred_list in referrals.items():
        if str(referred_id) in referred_list:
            return int(referrer)
    return None

def format_user_info(user):
    username = user.username
    full_name = user.full_name or "بدون نام"
    user_id = user.id
    
    info = "━━━━━━━━━━━━━━━━━━\n"
    info += "👤 اطلاعات فرستنده:\n"
    info += "━━━━━━━━━━━━━━━━━━\n"
    info += f"📛 نام: {full_name}\n"
    if username:
        info += f"🔗 یوزرنیم: @{username}\n"
        info += f"🌐 لینک: t.me/{username}\n"
    else:
        info += f"🔗 یوزرنیم: ندارد\n"
        info += f"🌐 لینک: ندارد\n"
    info += f"🆔 آیدی عددی: {user_id}\n"
    info += "━━━━━━━━━━━━━━━━━━"
    
    return info

# ========== State Machines ==========
class UserState(StatesGroup):
    waiting_anonymous = State()
    waiting_identified = State()
    adding_promo_name = State()
    adding_promo_link = State()
    changing_channel_id = State()
    changing_channel_link = State()
    adding_proxy = State()
    setting_referral_count = State()

# ========== Keyboards ==========
def join_channel_keyboard():
    channel_link = get_channel_link()
    buttons = [[InlineKeyboardButton(text="📢 عضویت در کانال", url=channel_link)]]
    if is_promo_enabled():
        promo_channels = get_promo_channels()
        for channel in promo_channels:
            buttons.append([InlineKeyboardButton(text=f"📣 {channel['name']}", url=channel['link'])])
    buttons.append([InlineKeyboardButton(text="✅ عضو شدم، بررسی کن", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_menu_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton(text="📰 موضوع روز", callback_data="daily_topic")],
        [InlineKeyboardButton(text="📩 پیام ناشناس", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 پیام با هویت", callback_data="send_id")],
        [InlineKeyboardButton(text="🎁 پروکسی هدیه", callback_data="free_proxy")],
        [InlineKeyboardButton(text="📜 قوانین", callback_data="rules")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_panel_keyboard():
    force_status = "✅ فعال" if is_force_join_enabled() else "❌ غیرفعال"
    promo_status = "✅ نمایش" if is_promo_enabled() else "❌ مخفی"
    proxy_status = "✅ فعال" if is_proxy_enabled() else "❌ غیرفعال"
    promo_count = len(get_promo_channels())
    proxy_count = len(load_proxies())
    channel_id = get_channel_id()
    required_referrals = get_required_referrals()
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔒 عضویت اجباری: {force_status}", callback_data="toggle_force_join")],
        [InlineKeyboardButton(text=f"📣 تبلیغات ({promo_count}): {promo_status}", callback_data="promo_settings")],
        [InlineKeyboardButton(text=f"🎁 پروکسی ({proxy_count}): {proxy_status}", callback_data="proxy_settings")],
        [InlineKeyboardButton(text=f"👥 دعوت مورد نیاز: {required_referrals}", callback_data="set_referral_count")],
        [InlineKeyboardButton(text=f"📂 کانال: {channel_id[:15]}...", callback_data="change_channel")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

def promo_settings_keyboard():
    promo_channels = get_promo_channels()
    buttons = []
    for i, channel in enumerate(promo_channels):
        buttons.append([
            InlineKeyboardButton(text=f"📝 {channel['name']}", callback_data=f"view_promo_{i}"),
            InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_promo_{i}")
        ])
    buttons.append([InlineKeyboardButton(text="➕ افزودن کانال جدید", callback_data="add_promo")])
    promo_status = "✅ نمایش" if is_promo_enabled() else "❌ مخفی"
    buttons.append([InlineKeyboardButton(text=f"🔕 تغییر وضعیت: {promo_status}", callback_data="toggle_promo")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def proxy_settings_keyboard():
    proxies = load_proxies()
    buttons = []
    for i, proxy in enumerate(proxies):
        proxy_short = proxy[:30] + "..." if len(proxy) > 30 else proxy
        buttons.append([InlineKeyboardButton(text=f"🗑️ {proxy_short}", callback_data=f"delete_proxy_{i}")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن پروکسی جدید", callback_data="add_proxy")])
    proxy_status = "✅ فعال" if is_proxy_enabled() else "❌ غیرفعال"
    buttons.append([InlineKeyboardButton(text=f"🔕 تغییر وضعیت: {proxy_status}", callback_data="toggle_proxy")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_menu_with_admin_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton(text="📰 موضوع روز", callback_data="daily_topic")],
        [InlineKeyboardButton(text="📩 پیام ناشناس", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 پیام با هویت", callback_data="send_id")],
        [InlineKeyboardButton(text="🎁 پروکسی هدیه", callback_data="free_proxy")],
        [InlineKeyboardButton(text="📜 قوانین", callback_data="rules")],
        [InlineKeyboardButton(text="⚙️ پنل مدیریت", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

def proxy_keyboard(user_id):
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=referral_link)],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

# ========== Handlers ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    channel_id = get_channel_id()
    
    # بررسی لینک دعوت
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != user_id:
                add_referral(referrer_id, user_id)
                await bot.send_message(
                    referrer_id, 
                    f"🎉 یک نفر با لینک دعوت شما عضو شد!\nتعداد دعوت‌های شما: {get_referral_count(referrer_id)}"
                )
        except:
            pass
    
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await message.answer("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
                return
        except TelegramBadRequest:
            await message.answer("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
            return

    await message.answer("👋 خوش آمدید به کانال خودتون❤️\nمارو به دوستاتون معرفی کنید!")
    topic = load_topic()
    await message.answer(f"📰 موضوع روز کانال:\n\n✨ {topic}")
    
    if str(user_id) == ADMIN_ID:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
    else:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))

@dp.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery):
    channel_id = get_channel_id()
    if not is_force_join_enabled():
        await callback.message.edit_text("✅ عضویت اجباری غیرفعال است!")
        topic = load_topic()
        await callback.message.answer(f"📰 موضوع روز کانال:\n\n✨ {topic}")
        user_id = callback.from_user.id
        if str(user_id) == ADMIN_ID:
            await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
        else:
            await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))
        return
    
    try:
        member = await bot.get_chat_member(channel_id, callback.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            await callback.message.edit_text("✅ عضویت تایید شد!")
            topic = load_topic()
            await callback.message.answer(f"📰 موضوع روز کانال:\n\n✨ {topic}")
            user_id = callback.from_user.id
            if str(user_id) == ADMIN_ID:
                await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
            else:
                await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))
        else:
            await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
    except:
        await callback.answer("❌ هنوز عضو کانال نیستی!", show_alert=True)

@dp.callback_query(F.data == "daily_topic")
async def show_daily_topic(callback: CallbackQuery):
    topic = load_topic()
    await callback.answer(f"📰 موضوع روز:\n\n✨ {topic}", show_alert=True)
    
    user_id = callback.from_user.id
    if str(user_id) == ADMIN_ID:
        await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
    else:
        await callback.message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))

@dp.callback_query(F.data == "free_proxy")
async def free_proxy(callback: CallbackQuery):
    if not is_proxy_enabled():
        await callback.answer("❌ بخش پروکسی موقتاً غیرفعال است!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
            return
    
    can_access, last_access = can_user_access_proxy(user_id)
    if not can_access:
        time_left = timedelta(days=1) - (datetime.now() - last_access)
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        await callback.message.edit_text(
            f"⚠️ شما قبلاً پروکسی دریافت کرده‌اید!\n\n"
            f"⏰ زمان باقی‌مانده تا دریافت مجدد:\n"
            f"{hours} ساعت و {minutes} دقیقه\n\n"
            f"💡 با دعوت دوستانتان می‌توانید پروکسی بیشتری دریافت کنید!",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    proxies = load_proxies()
    if not proxies:
        await callback.message.edit_text("⚠️ در حال حاضر پروکسی موجود نیست!", reply_markup=back_to_menu_keyboard())
        return
    
    referral_count = get_referral_count(user_id)
    required_referrals = get_required_referrals()
    
    # انتخاب پروکسی بر اساس تعداد دعوت
    if referral_count >= required_referrals:
        # پروکسی ویژه برای کسانی که دعوت کرده‌اند
        proxy_text = random.choice(proxies)
        record_proxy_access(user_id, bonus=True)
        
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        await callback.message.edit_text(
            f"🎁 پروکسی ویژه شما (به خاطر دعوت {referral_count} نفر):\n\n"
            f"`{proxy_text}`\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"هر روز از ما\n"
            f"پروکسی رایگان هدیه بگیرید😻\n\n"
            f"برای دوستات هم بفرست تا همیشه متصل باشن🤝\n\n"
            f"🔗 لینک دعوت شما:\n`{referral_link}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 کپی پروکسی", copy_text=proxy_text)],
                [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=referral_link)],
                [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
            ])
        )
    else:
        # پروکسی معمولی
        proxy_text = random.choice(proxies)
        record_proxy_access(user_id, bonus=False)
        
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        await callback.message.edit_text(
            f"🎁 پروکسی رایگان شما:\n\n"
            f"`{proxy_text}`\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"هر روز از ما\n"
            f"پروکسی رایگان هدیه بگیرید😻\n\n"
            f"💡 با دعوت {required_referrals - referral_count} نفر دیگر، پروکسی ویژه دریافت کنید!\n\n"
            f"🔗 لینک دعوت شما:\n`{referral_link}`\n\n"
            f"برای دوستات هم بفرست تا همیشه متصل باشن🤝",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 کپی پروکسی", copy_text=proxy_text)],
                [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=referral_link)],
                [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
            ])
        )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    
    force_status = "✅ فعال" if is_force_join_enabled() else "❌ غیرفعال"
    promo_status = "✅ نمایش" if is_promo_enabled() else "❌ مخفی"
    proxy_status = "✅ فعال" if is_proxy_enabled() else "❌ غیرفعال"
    promo_count = len(get_promo_channels())
    proxy_count = len(load_proxies())
    channel_id = get_channel_id()
    channel_link = get_channel_link()
    required_referrals = get_required_referrals()
    
    await callback.message.edit_text(
        f"⚙️ پنل مدیریت\n\n"
        f"🔒 عضویت اجباری: {force_status}\n"
        f"📣 تبلیغات: {promo_count}\n"
        f"🔕 نمایش تبلیغات: {promo_status}\n"
        f"🎁 پروکسی: {proxy_count}\n"
        f"🔕 وضعیت پروکسی: {proxy_status}\n"
        f"👥 دعوت مورد نیاز: {required_referrals}\n"
        f"📂 کانال: {channel_id}\n"
        f"🔗 لینک: {channel_link}", 
        reply_markup=admin_panel_keyboard()
    )

@dp.callback_query(F.data == "proxy_settings")
async def proxy_settings(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    
    proxies = load_proxies()
    proxy_status = "✅ فعال" if is_proxy_enabled() else "❌ غیرفعال"
    text = f"🎁 مدیریت پروکسی‌ها\n\nوضعیت: {proxy_status}\n\n"
    if proxies:
        text += f"تعداد پروکسی‌ها: {len(proxies)}\n\n"
        for i, proxy in enumerate(proxies[:5], 1):
            proxy_short = proxy[:40] + "..." if len(proxy) > 40 else proxy
            text += f"{i}. {proxy_short}\n"
    else:
        text += "هیچ پروکسی اضافه نشده!\n\n"
    
    await callback.message.edit_text(text, reply_markup=proxy_settings_keyboard())

@dp.callback_query(F.data == "add_proxy")
async def add_proxy_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    await state.set_state(UserState.adding_proxy)
    await callback.message.edit_text("پروکسی جدید را وارد کنید:\n\nمثال:\nvless://uuid@server:port")

@dp.message(UserState.adding_proxy)
async def add_proxy(message: Message, state: FSMContext):
    if not message.text:
        return
    proxy_string = message.text.strip()
    add_proxy(proxy_string)
    await message.answer(f"✅ پروکسی اضافه شد!", reply_markup=proxy_settings_keyboard())
    await state.clear()

@dp.callback_query(F.data.startswith("delete_proxy_"))
async def delete_proxy_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    index = int(callback.data.split("_")[-1])
    if remove_proxy(index):
        await callback.message.edit_text("🗑️ پروکسی حذف شد!", reply_markup=proxy_settings_keyboard())

@dp.callback_query(F.data == "toggle_proxy")
async def toggle_proxy_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    new_status = toggle_proxy()
    status_text = "✅ فعال" if new_status else "❌ غیرفعال"
    await callback.message.edit_text(f"وضعیت پروکسی {status_text} شد!", reply_markup=proxy_settings_keyboard())

@dp.callback_query(F.data == "set_referral_count")
async def set_referral_count_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    current = get_required_referrals()
    await state.set_state(UserState.setting_referral_count)
    await callback.message.edit_text(f"تعداد فعلی دعوت مورد نیاز: {current}\n\nلطفاً عدد جدید را وارد کنید:")

@dp.message(UserState.setting_referral_count)
async def set_referral_count(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید!")
        return
    count = int(message.text)
    if count < 1:
        await message.answer("❌ عدد باید حداقل 1 باشد!")
        return
    set_required_referrals(count)
    await message.answer(f"✅ تعداد دعوت مورد نیاز به {count} تغییر کرد!", reply_markup=admin_panel_keyboard())
    await state.clear()

@dp.callback_query(F.data == "toggle_force_join")
async def toggle_force_join_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    new_status = toggle_force_join()
    status_text = "✅ فعال" if new_status else "❌ غیرفعال"
    await callback.message.edit_text(f"✅ عضویت اجباری {status_text} شد!", reply_markup=admin_panel_keyboard())

@dp.callback_query(F.data == "change_channel")
async def change_channel_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    current_id = get_channel_id()
    current_link = get_channel_link()
    await state.set_state(UserState.changing_channel_id)
    await callback.message.edit_text(f"📂 تغییر کانال مبدا\n\nکانال فعلی: {current_id}\nلینک فعلی: {current_link}\n\nلطفاً آیدی عددی کانال جدید رو وارد کنید:\n(مثال: -1001234567890)")

@dp.message(UserState.changing_channel_id)
async def change_channel_id(message: Message, state: FSMContext):
    if not message.text:
        return
    channel_id = message.text.strip()
    await state.update_data(channel_id=channel_id)
    await state.set_state(UserState.changing_channel_link)
    await message.answer("حالا لینک کانال جدید رو وارد کنید:\nمثال: https://t.me/channelname")

@dp.message(UserState.changing_channel_link)
async def change_channel_link(message: Message, state: FSMContext):
    if not message.text:
        return
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channel_link = message.text.strip()
    if not channel_link.startswith("https://t.me/"):
        await message.answer("❌ لینک نامعتبر است! باید با https://t.me/ شروع بشه.")
        return
    set_channel(channel_id, channel_link)
    await message.answer(f"✅ کانال مبدا تغییر کرد!\nآیدی: {channel_id}\nلینک: {channel_link}", reply_markup=admin_panel_keyboard())
    await state.clear()

@dp.callback_query(F.data == "promo_settings")
async def promo_settings(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    promo_channels = get_promo_channels()
    promo_status = "✅ نمایش" if is_promo_enabled() else "❌ مخفی"
    text = f"📣 مدیریت تبلیغات\n\nوضعیت: {promo_status}\n\n"
    if promo_channels:
        for i, channel in enumerate(promo_channels, 1):
            text += f"{i}. {channel['name']}\n   {channel['link']}\n\n"
    else:
        text += "هیچ کانالی اضافه نشده!\n\n"
    await callback.message.edit_text(text, reply_markup=promo_settings_keyboard())

@dp.callback_query(F.data == "toggle_promo")
async def toggle_promo_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    new_status = toggle_promo()
    status_text = "✅ نمایش" if new_status else "❌ مخفی"
    await callback.message.edit_text(f"وضعیت نمایش تبلیغات {status_text} شد!", reply_markup=promo_settings_keyboard())

@dp.callback_query(F.data.startswith("delete_promo_"))
async def delete_promo_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    index = int(callback.data.split("_")[-1])
    promo_channels = get_promo_channels()
    if 0 <= index < len(promo_channels):
        channel_name = promo_channels[index]['name']
        remove_promo_channel(index)
        await callback.message.edit_text(f"🗑️ کانال حذف شد: {channel_name}", reply_markup=promo_settings_keyboard())

@dp.callback_query(F.data == "add_promo")
async def add_promo_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    await state.set_state(UserState.adding_promo_name)
    await callback.message.edit_text("نام کانال تبلیغاتی رو وارد کنید:")

@dp.message(UserState.adding_promo_name)
async def add_promo_name(message: Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(promo_name=message.text)
    await state.set_state(UserState.adding_promo_link)
    await message.answer("لینک کانال رو وارد کنید:\nمثال: https://t.me/channelname")

@dp.message(UserState.adding_promo_link)
async def add_promo_link(message: Message, state: FSMContext):
    if not message.text:
        return
    data = await state.get_data()
    name = data.get("promo_name")
    link = message.text
    if not link.startswith("https://t.me/"):
        await message.answer("❌ لینک نامعتبر است!")
        return
    add_promo_channel(name, link)
    await message.answer(f"✅ کانال اضافه شد!\nنام: {name}\nلینک: {link}", reply_markup=promo_settings_keyboard())
    await state.clear()

@dp.callback_query(F.data.startswith("view_promo_"))
async def view_promo_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    index = int(callback.data.split("_")[-1])
    promo_channels = get_promo_channels()
    if 0 <= index < len(promo_channels):
        channel = promo_channels[index]
        await callback.message.edit_text(f"نام: {channel['name']}\nلینک: {channel['link']}", reply_markup=promo_settings_keyboard())

@dp.callback_query(F.data == "send_anon")
async def start_anonymous(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
            return
    
    if has_user_sent(user_id):
        await callback.message.edit_text("⚠️ شما در طول روز یک بار می‌توانید پیام ارسال کنید!", reply_markup=back_to_menu_keyboard())
        return
    
    topic = load_topic()
    await state.set_state(UserState.waiting_anonymous)
    await callback.message.edit_text(
        f"📰 موضوع امروز: {topic}\n\n"
        f"📩 پیام ناشناس\n\n"
        f"پیام متنی خودتون رو ارسال کنید\nاین پیام بدون یوزرنیم شما فوروارد می‌شه🙏\n\n"
        f"🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n"
        f"⚠️ برای انصراف دکمه پایین رو بزن.", 
        reply_markup=back_to_menu_keyboard()
    )

@dp.callback_query(F.data == "send_id")
async def start_identified(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
            return
    
    if has_user_sent(user_id):
        await callback.message.edit_text("⚠️ شما در طول روز یک بار می‌توانید پیام ارسال کنید!", reply_markup=back_to_menu_keyboard())
        return
    
    topic = load_topic()
    await state.set_state(UserState.waiting_identified)
    await callback.message.edit_text(
        f"📰 موضوع امروز: {topic}\n\n"
        f"👤 پیام با هویت\n\n"
        f"پیام متنی خودتون رو ارسال کنید\nاین پیام با یوزرنیم شما فوروارد می‌شه😄\n\n"
        f"🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n"
        f"⚠️ برای انصراف دکمه پایین رو بزن.", 
        reply_markup=back_to_menu_keyboard()
    )

@dp.message(UserState.waiting_anonymous)
async def receive_anonymous(message: Message, state: FSMContext):
    if not message.text:
        return
    user_id = message.from_user.id
    add_user_to_sent(user_id)
    admin_id = int(ADMIN_ID)
    
    user_info = format_user_info(message.from_user)
    await bot.send_message(chat_id=admin_id, text=user_info)
    
    await bot.send_message(chat_id=admin_id, text="📩 پیام ناشناس جدید:")
    await bot.send_chat_action(chat_id=admin_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)
    await bot.send_message(chat_id=admin_id, text=message.text)
    
    await message.answer("✅ پیام شما با موفقیت به دست ادمین رسید مرسی❤️")
    
    if str(user_id) == ADMIN_ID:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
    else:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))
    
    await state.clear()

@dp.message(UserState.waiting_identified)
async def receive_identified(message: Message, state: FSMContext):
    if not message.text:
        return
    user_id = message.from_user.id
    add_user_to_sent(user_id)
    
    user = message.from_user
    username = user.username
    full_name = user.full_name or "کاربر"
    signature = f"@{username}" if username else full_name
    
    admin_id = int(ADMIN_ID)
    
    user_info = format_user_info(user)
    await bot.send_message(chat_id=admin_id, text=user_info)
    
    combined_text = f"👤 پیام با هویت:\n\n{message.text}\n\n— {signature}"
    await bot.send_message(chat_id=admin_id, text=combined_text)
    
    await message.answer("✅ پیام شما با موفقیت به دست ادمین رسید مرسی❤️")
    
    if str(user_id) == ADMIN_ID:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
    else:
        await message.answer("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))
    
    await state.clear()

@dp.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery):
    rules_text = (
        "📜 قوانین ارسال متن\n\n"
        "پیام شما پس از ارسال به دست ادمین کانال می‌رسد\n"
        "لذا موارد زیر اگر رعایت نشود پیام شما فوروارد نخواهد شد!\n\n"
        "1️⃣ بی‌ادبی و توهین\n"
        "2️⃣ سیاسی\n"
        "3️⃣ نداشتن ارتباط با موضوع روز کانال\n"
        "4️⃣ داشتن لینک و یا موارد تبلیغاتی\n"
        "5️⃣ اسپم و فلود"
    )
    await callback.message.edit_text(rules_text, reply_markup=back_to_menu_keyboard())

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if str(user_id) == ADMIN_ID:
        await callback.message.edit_text("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_with_admin_keyboard(user_id))
    else:
        await callback.message.edit_text("از منوی زیر یکی رو انتخاب کن:", reply_markup=main_menu_keyboard(user_id))

@dp.channel_post()
async def channel_post_handler(message: Message):
    text = message.text or ""
    logging.info(f"پیام کانال دریافت شد: {text}")
    
    if text.startswith("📌"):
        topic = text.replace("📌", "").strip()
        if topic:
            save_topic(topic)
            clear_sent_users()
            admin_id = int(ADMIN_ID)
            await bot.send_message(
                chat_id=admin_id, 
                text=f"✅ موضوع روز بروزرسانی شد:\n\n📰 {topic}\n\n🗑️ لیست کاربران پاک شد."
            )

async def main():
    logging.info("Bot is starting on Hetzner Server...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
