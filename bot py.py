import os
import json
import logging
import asyncio
import random
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8916837966:AAHaYZGz2X8OsI5DuZ9_h9RAj5oVDgrhw2s"
ADMIN_ID = "6282695098"
MARZBAN_URL = "https://panel.shahinfree.shop"
MARZBAN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzaGFoaW4iLCJhY2Nlc3MiOiJhZG1pbiIsImlhdCI6MTc4NTMzMTU2MSwiZXhwIjoxNzg1NDE3OTYxfQ.RoO5wb6GcELmeltlbLeJvmYbHqjk9AdFa5gb60M7V6o"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TOPIC_FILE = "daily_topic.txt"
SENT_USERS_FILE = "sent_users.json"
SETTINGS_FILE = "settings.json"
PROXIES_FILE = "proxies.json"
PROXY_ACCESS_FILE = "proxy_access.json"
REFERRALS_FILE = "referrals.json"
CONFIG_ACCESS_FILE = "config_access.json"
USER_PARTICIPATION_FILE = "user_participation.json"
USER_HISTORY_FILE = "user_history.json"
CHANNEL_LINKS_FILE = "channel_links.json"
TOPIC_IDEAS_FILE = "topic_ideas.json"

def load_user_history():
    try:
        with open(USER_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_user_history(data):
    with open(USER_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_user_to_history(user_id, username=None, full_name=None):
    history = load_user_history()
    user_key = str(user_id)
    now = datetime.now().isoformat()
    if user_key not in history:
        history[user_key] = {"first_seen": now, "last_seen": now, "username": username, "full_name": full_name, "message_count": 1}
    else:
        history[user_key]["last_seen"] = now
        history[user_key]["message_count"] += 1
        if username: history[user_key]["username"] = username
        if full_name: history[user_key]["full_name"] = full_name
    save_user_history(history)

def cleanup_old_users(days=10):
    history = load_user_history()
    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    users_to_remove = [uid for uid, data in history.items() if datetime.fromisoformat(data["last_seen"]) < cutoff_date]
    for uid in users_to_remove:
        del history[uid]
    if users_to_remove:
        save_user_history(history)
    return len(users_to_remove)

def get_active_users():
    cleanup_old_users(10)
    return load_user_history()

def load_channel_links():
    try:
        with open(CHANNEL_LINKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_channel_links(links):
    with open(CHANNEL_LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def add_channel_link(name, link):
    links = load_channel_links()
    links.append({"name": name, "link": link})
    save_channel_links(links)

def remove_channel_link(index):
    links = load_channel_links()
    if 0 <= index < len(links):
        links.pop(index)
        save_channel_links(links)
        return True
    return False

def get_channel_links():
    return load_channel_links()

def load_topic_ideas():
    try:
        with open(TOPIC_IDEAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_topic_ideas(ideas):
    with open(TOPIC_IDEAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ideas, f, ensure_ascii=False, indent=2)

def add_topic_idea(user_id, username, full_name, idea):
    ideas = load_topic_ideas()
    ideas.append({"user_id": user_id, "username": username, "full_name": full_name, "idea": idea, "timestamp": datetime.now().isoformat()})
    save_topic_ideas(ideas)

def get_topic_ideas():
    return load_topic_ideas()

def clear_topic_ideas():
    save_topic_ideas([])

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
    return str(user_id) in load_sent_users()

def add_user_to_sent(user_id):
    users = load_sent_users()
    users.append(str(user_id))
    save_sent_users(users)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"force_join": True, "promo_channels": [], "show_promo": True, "channel_id": "", "channel_link": "", "required_referrals": 2, "proxy_enabled": True}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_channel_id():
    return load_settings().get("channel_id", "")

def get_channel_link():
    return load_settings().get("channel_link", "")

def set_channel(channel_id, channel_link):
    settings = load_settings()
    settings["channel_id"] = channel_id
    settings["channel_link"] = channel_link
    save_settings(settings)

def is_force_join_enabled():
    return load_settings().get("force_join", True)

def toggle_force_join():
    settings = load_settings()
    settings["force_join"] = not settings.get("force_join", True)
    save_settings(settings)
    return settings["force_join"]

def get_promo_channels():
    return load_settings().get("promo_channels", [])

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
    return load_settings().get("show_promo", True)

def toggle_promo():
    settings = load_settings()
    settings["show_promo"] = not settings.get("show_promo", True)
    save_settings(settings)
    return settings["show_promo"]

def get_required_referrals():
    return load_settings().get("required_referrals", 2)

def set_required_referrals(count):
    settings = load_settings()
    settings["required_referrals"] = count
    save_settings(settings)

def is_proxy_enabled():
    return load_settings().get("proxy_enabled", True)

def toggle_proxy():
    settings = load_settings()
    settings["proxy_enabled"] = not settings.get("proxy_enabled", True)
    save_settings(settings)
    return settings["proxy_enabled"]

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

def load_proxy_access():
    try:
        with open(PROXY_ACCESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_proxy_access(data):
    with open(PROXY_ACCESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def can_user_access_proxy(user_id):
    data = load_proxy_access()
    key = str(user_id)
    if key not in data:
        return True, None
    last = datetime.fromisoformat(data[key]["last_access"])
    if datetime.now() - last < timedelta(days=1):
        return False, last
    return True, None

def record_proxy_access(user_id, bonus=False):
    data = load_proxy_access()
    data[str(user_id)] = {"last_access": datetime.now().isoformat(), "bonus_used": bonus}
    save_proxy_access(data)

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
    key = str(referrer_id)
    if key not in referrals:
        referrals[key] = []
    if str(referred_id) not in referrals[key]:
        referrals[key].append(str(referred_id))
        save_referrals(referrals)
        return True
    return False

def get_referral_count(user_id):
    return len(load_referrals().get(str(user_id), []))

def format_user_info(user):
    username = user.username
    full_name = user.full_name or "بدون نام"
    user_id = user.id
    info = "━━━━━━━━━━━━━━━━━━\n اطلاعات فرستنده:\n━━━━━━━━━━━━━━━━━━\n"
    info += f"📛 نام: {full_name}\n"
    if username:
        info += f"🔗 یوزرنیم: @{username}\n🌐 لینک: t.me/{username}\n"
    else:
        info += "🔗 یوزرنیم: ندارد\n🌐 لینک: ندارد\n"
    info += f" آیدی عددی: {user_id}\n━━━━━━━━━━━━━━━━━━"
    return info

def get_marzban_headers():
    return {"Authorization": f"Bearer {MARZBAN_TOKEN}", "Content-Type": "application/json"}

def create_or_get_config(user_id):
    username = f"user_{user_id}"
    headers = get_marzban_headers()
    
    # بررسی وجود کاربر
    res = requests.get(f"{MARZBAN_URL}/api/user/{username}", headers=headers, verify=False)
    if res.status_code == 200:
        return res.json().get("subscription_url", "خطا")
    
    # ساخت کاربر جدید
    from datetime import datetime, timedelta
    expire_timestamp = int((datetime.now() + timedelta(hours=24)).timestamp())
    
    payload = {
        "username": username,
        "data_limit": 500 * 1024 * 1024,
        "expire": expire_timestamp,
        "inbounds": {
            "vmess": ["VMess"],
            "vless": ["VLESS"]
        },
        "proxies": {
            "vmess": {},
            "vless": {}
        },
        "status": "active"
    }
    
    # اصلاح: /api/user به جای /api/users
    res = requests.post(f"{MARZBAN_URL}/api/user", json=payload, headers=headers, verify=False)
    if res.status_code in [200, 201]:
        return res.json().get("subscription_url", "خطا")
    return f"خطا: {res.status_code}"


def load_config_access():
    try:
        with open(CONFIG_ACCESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_config_access(data):
    with open(CONFIG_ACCESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def can_user_get_config(user_id):
    data = load_config_access()
    key = str(user_id)
    if key not in data:
        return True, 0
    last = datetime.fromisoformat(data[key]["last_access"])
    hours = (datetime.now() - last).total_seconds() / 3600
    if hours >= 24:
        return True, 0
    if get_referral_count(user_id) >= 4 and not data[key].get("bonus_used", False):
        return True, 4
    return False, int(24 - hours)

def record_config_access(user_id, is_bonus=False):
    data = load_config_access()
    data[str(user_id)] = {"last_access": datetime.now().isoformat(), "bonus_used": is_bonus}
    save_config_access(data)

def load_user_participation():
    try:
        with open(USER_PARTICIPATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_user_participation(data):
    with open(USER_PARTICIPATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def has_user_participated(user_id):
    return str(user_id) in load_user_participation()

def mark_user_participated(user_id):
    data = load_user_participation()
    data[str(user_id)] = {"participated_at": datetime.now().isoformat()}
    save_user_participation(data)

class UserState(StatesGroup):
    waiting_anonymous = State()
    waiting_identified = State()
    adding_promo_name = State()
    adding_promo_link = State()
    changing_channel_id = State()
    changing_channel_link = State()
    adding_proxy = State()
    setting_referral_count = State()
    adding_topic_idea = State()
    adding_channel_link_name = State()
    adding_channel_link_url = State()

def join_channel_keyboard():
    channel_link = get_channel_link()
    buttons = [[InlineKeyboardButton(text="📢 عضویت در کانال", url=channel_link)]]
    if is_promo_enabled():
        for ch in get_promo_channels():
            buttons.append([InlineKeyboardButton(text=f" {ch['name']}", url=ch['link'])])
    buttons.append([InlineKeyboardButton(text="✅ عضو شدم، بررسی کن", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel")],
        [InlineKeyboardButton(text="💡 ایده موضوع روز", callback_data="topic_idea")],
        [InlineKeyboardButton(text="📩 پیام ناشناس", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 پیام با هویت", callback_data="send_id")],
        [InlineKeyboardButton(text="🎁 پروکسی هدیه", callback_data="free_proxy")],
        [InlineKeyboardButton(text="🔑 دریافت کانفیگ 500 مگ", callback_data="get_config")],
        [InlineKeyboardButton(text="📜 قوانین و معرفی ما", callback_data="rules_and_about")],
    ])

def admin_only_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ پنل مدیریت", callback_data="admin_panel")],
    ])

def admin_panel_keyboard():
    force_status = "✅ فعال" if is_force_join_enabled() else "❌ غیرفعال"
    promo_status = "✅ نمایش" if is_promo_enabled() else "❌ مخفی"
    proxy_status = "✅ فعال" if is_proxy_enabled() else "❌ غیرفعال"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👥 یوزرها ({len(get_active_users())})", callback_data="view_users")],
        [InlineKeyboardButton(text=f" ایده‌ها ({len(get_topic_ideas())})", callback_data="view_ideas")],
        [InlineKeyboardButton(text=f"🔒 عضویت اجباری: {force_status}", callback_data="toggle_force_join")],
        [InlineKeyboardButton(text=f"📣 تبلیغات: {promo_status}", callback_data="promo_settings")],
        [InlineKeyboardButton(text=f"🎁 پروکسی: {proxy_status}", callback_data="proxy_settings")],
        [InlineKeyboardButton(text="🔗 لینک‌های کانال", callback_data="channel_links_settings")],
        [InlineKeyboardButton(text=f" دعوت: {get_required_referrals()}", callback_data="set_referral_count")],
        [InlineKeyboardButton(text=f"📂 کانال: {get_channel_id()[:15]}...", callback_data="change_channel")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

def users_list_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="️ پاکسازی دستی", callback_data="manual_cleanup")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")]
    ])

def ideas_list_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ پاکسازی همه", callback_data="clear_ideas")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")]
    ])

def channel_links_keyboard():
    links = get_channel_links()
    buttons = []
    for i, link in enumerate(links):
        buttons.append([
            InlineKeyboardButton(text=f"🔗 {link['name']}", callback_data=f"view_link_{i}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"delete_link_{i}")
        ])
    buttons.append([InlineKeyboardButton(text=" افزودن لینک", callback_data="add_channel_link")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def promo_settings_keyboard():
    buttons = []
    for i, ch in enumerate(get_promo_channels()):
        buttons.append([InlineKeyboardButton(text=f"📝 {ch['name']}", callback_data=f"view_promo_{i}"), InlineKeyboardButton(text="🗑️", callback_data=f"delete_promo_{i}")])
    buttons.append([InlineKeyboardButton(text=" افزودن", callback_data="add_promo")])
    buttons.append([InlineKeyboardButton(text=f" وضعیت: {'نمایش' if is_promo_enabled() else 'مخفی'}", callback_data="toggle_promo")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def proxy_settings_keyboard():
    buttons = []
    for i, p in enumerate(load_proxies()):
        short = p[:30] + "..." if len(p) > 30 else p
        buttons.append([InlineKeyboardButton(text=f"🗑️ {short}", callback_data=f"delete_proxy_{i}")])
    buttons.append([InlineKeyboardButton(text="➕ افزودن پروکسی", callback_data="add_proxy")])
    buttons.append([InlineKeyboardButton(text=f"🔕 وضعیت: {'فعال' if is_proxy_enabled() else 'غیرفعال'}", callback_data="toggle_proxy")])
    buttons.append([InlineKeyboardButton(text=" بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

def back_menu_with_full_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")],
        [InlineKeyboardButton(text=" پیام ناشناس", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 پیام با هویت", callback_data="send_id")]
    ])

async def send_panel(callback_or_message, user_id, edit=False):
    topic = load_topic()
    text = f"📰 <b>موضوع روز کانال:</b>\n\n✨ {topic}\n\nاز منوی زیر یکی را انتخاب کنید:"
    kb = main_menu_keyboard()
    if edit:
        try:
            await callback_or_message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback_or_message.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback_or_message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    channel_id = get_channel_id()
    add_user_to_history(user_id, message.from_user.username, message.from_user.full_name)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != user_id:
                add_referral(referrer_id, user_id)
                await bot.send_message(referrer_id, f" یک نفر با لینک دعوت شما عضو شد!\nتعداد دعوت‌های شما: {get_referral_count(referrer_id)}")
        except:
            pass
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await message.answer("️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
                return
        except TelegramBadRequest:
            await message.answer("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
            return
    await message.answer("👋 خوش آمدید به کانال خودتون❤️\nمارو به دوستاتون معرفی کنید!")
    if str(user_id) == ADMIN_ID:
        await message.answer("⚙️ پنل مدیریت:", reply_markup=admin_panel_keyboard())
    else:
        await send_panel(message, user_id)

@dp.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery):
    channel_id = get_channel_id()
    if not is_force_join_enabled():
        await callback.message.edit_text("✅ عضویت اجباری غیرفعال است!")
        await send_panel(callback, callback.from_user.id, edit=True)
        return
    try:
        member = await bot.get_chat_member(channel_id, callback.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            await callback.message.edit_text("✅ عضویت تایید شد!")
            await send_panel(callback, callback.from_user.id, edit=True)
        else:
            await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
    except:
        await callback.answer("❌ هنوز عضو کانال نیستی!", show_alert=True)

@dp.callback_query(F.data == "refresh_panel")
async def refresh_panel(callback: CallbackQuery):
    await send_panel(callback, callback.from_user.id, edit=True)

@dp.callback_query(F.data == "topic_idea")
async def topic_idea_intro(callback: CallbackQuery):
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("️ برای ارسال ایده، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ برای ارسال ایده، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
            return
    text = "💡 <b>ایده موضوع روز</b>\n\nاگر ایده‌ای برای موضوع بحث فردا دارید، آن را برای ما بفرستید!\n\n📝 ایده شما پس از بررسی توسط ادمین، ممکن است به عنوان موضوع روز انتخاب شود.\n\nلطفاً ایده خود را در یک پیام کوتاه بنویسید:"
    await callback.message.edit_text(text, reply_markup=back_menu_keyboard(), parse_mode="HTML")
    await UserState.adding_topic_idea.set()

@dp.message(UserState.adding_topic_idea)
async def receive_topic_idea(message: Message, state: FSMContext):
    if not message.text:
        return
    user_id = message.from_user.id
    username = message.from_user.username or "ندارد"
    full_name = message.from_user.full_name or "بدون نام"
    add_topic_idea(user_id, username, full_name, message.text)
    admin_id = int(ADMIN_ID)
    idea_text = f"💡 <b>ایده جدید برای موضوع روز</b>\n\n👤 از: {full_name}\n یوزرنیم: @{username}\n🆔 آیدی: {user_id}\n\n📝 <b>ایده:</b>\n{message.text}"
    await bot.send_message(chat_id=admin_id, text=idea_text, parse_mode="HTML")
    await message.answer("✅ ایده شما با موفقیت ثبت شد!\n\nممنون از مشارکت شما 💚", reply_markup=back_menu_keyboard())
    await state.clear()

@dp.callback_query(F.data == "get_config")
async def get_config_intro(callback: CallbackQuery):
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("⚠️ برای دریافت کانفیگ، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ برای دریافت کانفیگ، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
            return
    if not has_user_participated(user_id):
        text = "⚠️ <b>برای دریافت کانفیگ، ابتدا باید در موضوع روز نظر بدهید!</b>\n\nلطفاً از منوی اصلی، گزینه <b>'📩 پیام ناشناس'</b> یا <b>'👤 پیام با هویت'</b> را انتخاب کنید و نظر خود را درباره موضوع روز بنویسید.\n\nپس از ارسال نظر، می‌توانید کانفیگ رایگان دریافت کنید! "
        await callback.message.edit_text(text, reply_markup=back_menu_with_full_keyboard(), parse_mode="HTML")
        return
    text = " <b>دوستان \"حرفِ‌تو\" روزانه از ما کانفیگ پرسرعت و فعال با حجم 500 مگابایت رایگان دریافت کنید!</b>\n\nآیا مایل به دریافت کانفیگ هستید؟"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید و دریافت کانفیگ", callback_data="confirm_config")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "confirm_config")
async def confirm_config_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    can_access, info = can_user_get_config(user_id)
    if not can_access:
        hours_left = info
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = f"️ شما امروز قبلاً کانفیگ دریافت کرده‌اید!\n\n⏰ زمان باقی‌مانده تا دریافت مجدد رایگان: <b>{hours_left} ساعت</b>\n\n💡 <b>راه دریافت فوری:</b>\nاگر <b>4 نفر</b> را با لینک زیر به کانال دعوت کنید، بلافاصله یک کانفیگ دیگر دریافت می‌کنید!\n\n🔗 لینک دعوت شما:\n<code>{referral_link}</code>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=referral_link))],
            [InlineKeyboardButton(text="🔄 بررسی مجدد دعوت‌ها", callback_data="confirm_config")],
            [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    await callback.message.edit_text("⏳ در حال ساخت کانفیگ اختصاصی برای شما... لطفاً چند لحظه صبر کنید.")
    config_link = create_or_get_config(user_id)
    if config_link.startswith("خطا"):
        await callback.message.edit_text(f"❌ {config_link}\n\nلطفاً بعداً مجدداً تلاش کنید یا به ادمین پیام دهید.", reply_markup=back_menu_keyboard())
        return
    referrals = get_referral_count(user_id)
    is_bonus = referrals >= 4
    record_config_access(user_id, is_bonus=is_bonus)
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = f"✅ <b>کانفیگ شما با موفقیت ساخته شد!</b>\n\n📊 حجم: 500 مگابایت\n⏰ اعتبار: 24 ساعت\n\n🔗 <b>لینک اشتراک شما:</b>\n<code>{config_link}</code>\n\n💡 برای حمایت از ما، لینک دعوت خود را برای دوستانتان بفرستید:\n<code>{referral_link}</code>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی لینک اشتراک", copy_text=CopyTextButton(text=config_link))],
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=referral_link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "free_proxy")
async def free_proxy_intro(callback: CallbackQuery):
    if not is_proxy_enabled():
        await callback.answer("❌ بخش پروکسی موقتاً غیرفعال است!", show_alert=True)
        return
    user_id = callback.from_user.id
    channel_id = get_channel_id()
    if is_force_join_enabled() and channel_id:
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await callback.message.edit_text("⚠️ برای دریافت پروکسی، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ برای دریافت پروکسی، ابتدا باید در کانال عضو باشید.", reply_markup=join_channel_keyboard())
            return
    if not has_user_participated(user_id):
        text = "⚠️ <b>برای دریافت پروکسی، ابتدا باید در موضوع روز نظر بدهید!</b>\n\nلطفاً از منوی اصلی، گزینه <b>' پیام ناشناس'</b> یا <b>'👤 پیام با هویت'</b> را انتخاب کنید و نظر خود را درباره موضوع روز بنویسید.\n\nپس از ارسال نظر، می‌توانید پروکسی رایگان دریافت کنید! 💚"
        await callback.message.edit_text(text, reply_markup=back_menu_with_full_keyboard(), parse_mode="HTML")
        return
    text = "🎁 <b>دریافت پروکسی هدیه</b>\n\nما هر روز پروکسی‌های رایگان و پرسرعت در اختیار شما قرار می‌دهیم.\n\n⚠️ <b>قوانین:</b>\n• هر کاربر فقط <b>یک بار در 24 ساعت</b> می‌تواند پروکسی رایگان دریافت کند.\n• برای دریافت پروکسی نامحدود در همان روز، <b>2 نفر</b> را به کانال دعوت کنید.\n\nآیا مایل به دریافت پروکسی هستید؟"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید و دریافت پروکسی", callback_data="confirm_proxy")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "confirm_proxy")
async def confirm_proxy_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    can_access, last_access = can_user_access_proxy(user_id)
    if not can_access:
        time_left = timedelta(days=1) - (datetime.now() - last_access)
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = f"⚠️ شما امروز قبلاً پروکسی دریافت کرده‌اید!\n\n زمان باقی‌مانده تا دریافت مجدد: <b>{hours} ساعت و {minutes} دقیقه</b>\n\n💡 <b>راه دریافت فوری:</b>\nاگر <b>2 نفر</b> را با لینک زیر به کانال دعوت کنید، بلافاصله پروکسی ویژه دریافت می‌کنید!\n\n🔗 لینک دعوت شما:\n<code>{referral_link}</code>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=referral_link))],
            [InlineKeyboardButton(text="🔄 بررسی مجدد دعوت‌ها", callback_data="confirm_proxy")],
            [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    proxies = load_proxies()
    if not proxies:
        await callback.message.edit_text("⚠️ در حال حاضر پروکسی موجود نیست! لطفاً بعداً مراجعه کنید.", reply_markup=back_menu_keyboard())
        return
    referral_count = get_referral_count(user_id)
    required_referrals = get_required_referrals()
    proxy_text = random.choice(proxies)
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    if referral_count >= required_referrals:
        record_proxy_access(user_id, bonus=True)
        text = f"🎁 <b>پروکسی ویژه شما</b> (به خاطر دعوت {referral_count} نفر):\n\n<code>{proxy_text}</code>\n\n━━━━━━━━━━━━━━━━━━\nهر روز از ما پروکسی رایگان هدیه بگیرید 😻\n\n🔗 لینک دعوت شما:\n<code>{referral_link}</code>"
    else:
        record_proxy_access(user_id, bonus=False)
        text = f"🎁 <b>پروکسی رایگان شما:</b>\n\n<code>{proxy_text}</code>\n\n━━━━━━━━━━━━━━━━━━\nهر روز از ما پروکسی رایگان هدیه بگیرید 😻\n\n💡 با دعوت <b>{required_referrals - referral_count} نفر</b> دیگر، پروکسی ویژه و نامحدود دریافت کنید!\n\n🔗 لینک دعوت شما:\n<code>{referral_link}</code>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی پروکسی", copy_text=CopyTextButton(text=proxy_text))],
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=referral_link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "rules_and_about")
async def rules_and_about_handler(callback: CallbackQuery):
    channel_links = get_channel_links()
    text = " <b>درباره ما</b>\n\nبه کانال <b>\"حرفِ‌تو\"</b> خوش آمدید!\n\n🌐 ما فضایی برای بیان آزادانه نظرات و ایده‌های شما هستیم.\n\n💚 هر روز:\n• موضوع روز برای بحث و گفتگو\n• کانفیگ 500 مگابایت رایگان\n• پروکسی‌های پرسرعت هدیه\n\n"
    if channel_links:
        text += "🔗 <b>لینک‌های کانال‌های ما:</b>\n\n"
        for link in channel_links:
            text += f"• <a href=\"{link['link']}\">{link['name']}</a>\n"
        text += "\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n📜 <b>قوانین ارسال متن</b>\n\nپیام شما پس از ارسال به دست ادمین کانال می‌رسد\nلذا موارد زیر اگر رعایت نشود پیام شما فوروارد نخواهد شد!\n\n1️⃣ بی‌ادبی و توهین\n2️⃣ سیاسی\n3️ نداشتن ارتباط با موضوع روز کانال\n4️⃣ داشتن لینک و یا موارد تبلیغاتی\n5️⃣ اسپم و فلود\n\n🤝 با ما همراه باشید!"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.edit_text("⚙️ پنل مدیریت:", reply_markup=admin_panel_keyboard())

@dp.callback_query(F.data == "view_users")
async def view_users(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer(" دسترسی ندارید!", show_alert=True)
        return
    users = get_active_users()
    if not users:
        await callback.message.edit_text(" هیچ کاربری ثبت نشده است!", reply_markup=users_list_keyboard())
        return
    text = f"👥 <b>لیست کاربران فعال ({len(users)} نفر):</b>\n\n"
    for user_id, data in sorted(users.items(), key=lambda x: datetime.fromisoformat(x[1]["last_seen"]), reverse=True)[:20]:
        username = data.get("username", "ندارد")
        full_name = data.get("full_name", "بدون نام")
        last_seen = datetime.fromisoformat(data["last_seen"]).strftime("%Y-%m-%d %H:%M")
        msg_count = data.get("message_count", 0)
        text += f"🆔 {user_id}\n   👤 {full_name} (@{username})\n   📅 آخرین بازدید: {last_seen}\n   💬 تعداد پیام: {msg_count}\n\n"
    await callback.message.edit_text(text, reply_markup=users_list_keyboard())

@dp.callback_query(F.data == "manual_cleanup")
async def manual_cleanup(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    removed = cleanup_old_users(10)
    await callback.message.edit_text(f"✅ {removed} کاربر قدیمی پاک شد!", reply_markup=users_list_keyboard())

@dp.callback_query(F.data == "view_ideas")
async def view_ideas(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    ideas = get_topic_ideas()
    if not ideas:
        await callback.message.edit_text("💡 هیچ ایده‌ای ثبت نشده است!", reply_markup=ideas_list_keyboard())
        return
    text = f"💡 <b>ایده‌های موضوع روز ({len(ideas)} مورد):</b>\n\n"
    for i, idea in enumerate(ideas[-10:], 1):
        username = idea.get("username", "ندارد")
        full_name = idea.get("full_name", "بدون نام")
        idea_text = idea.get("idea", "")
        timestamp = datetime.fromisoformat(idea["timestamp"]).strftime("%Y-%m-%d %H:%M")
        text += f"{i}. 💬 {idea_text}\n   👤 {full_name} (@{username})\n   📅 {timestamp}\n\n"
    await callback.message.edit_text(text, reply_markup=ideas_list_keyboard())

@dp.callback_query(F.data == "clear_ideas")
async def clear_ideas(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    clear_topic_ideas()
    await callback.message.edit_text("🗑️ همه ایده‌ها پاک شد!", reply_markup=ideas_list_keyboard())

@dp.callback_query(F.data == "channel_links_settings")
async def channel_links_settings(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    links = get_channel_links()
    if not links:
        text = "🔗 <b>مدیریت لینک‌های کانال</b>\n\nهیچ لینکی اضافه نشده است!"
    else:
        text = f" <b>مدیریت لینک‌های کانال ({len(links)} مورد):</b>\n\n"
        for i, link in enumerate(links, 1):
            text += f"{i}. {link['name']}: {link['link']}\n\n"
    await callback.message.edit_text(text, reply_markup=channel_links_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "add_channel_link")
async def add_channel_link_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    await state.set_state(UserState.adding_channel_link_name)
    await callback.message.edit_text("نام لینک کانال را وارد کنید:")

@dp.message(UserState.adding_channel_link_name)
async def add_channel_link_name(message: Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(link_name=message.text)
    await state.set_state(UserState.adding_channel_link_url)
    await message.answer("لینک کانال را وارد کنید:\nمثال: https://t.me/channelname")

@dp.message(UserState.adding_channel_link_url)
async def add_channel_link_url(message: Message, state: FSMContext):
    if not message.text:
        return
    data = await state.get_data()
    name = data.get("link_name")
    link = message.text.strip()
    if not link.startswith("https://t.me/"):
        await message.answer(" لینک نامعتبر است! باید با https://t.me/ شروع شود.")
        return
    add_channel_link(name, link)
    await message.answer(f"✅ لینک اضافه شد!\nنام: {name}\nلینک: {link}", reply_markup=channel_links_keyboard())
    await state.clear()

@dp.callback_query(F.data.startswith("delete_link_"))
async def delete_channel_link(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    index = int(callback.data.split("_")[-1])
    if remove_channel_link(index):
        await callback.message.edit_text("🗑️ لینک حذف شد!", reply_markup=channel_links_keyboard())

@dp.callback_query(F.data.startswith("view_link_"))
async def view_channel_link(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    index = int(callback.data.split("_")[-1])
    links = get_channel_links()
    if 0 <= index < len(links):
        link = links[index]
        await callback.message.edit_text(f"نام: {link['name']}\nلینک: {link['link']}", reply_markup=channel_links_keyboard())

@dp.callback_query(F.data == "proxy_settings")
async def proxy_settings(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    proxies = load_proxies()
    proxy_status = "✅ فعال" if is_proxy_enabled() else " غیرفعال"
    text = f" مدیریت پروکسی‌ها\n\nوضعیت: {proxy_status}\n\n"
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
    await callback.message.edit_text(f" تغییر کانال مبدا\n\nکانال فعلی: {current_id}\nلینک فعلی: {current_link}\n\nلطفاً آیدی عددی کانال جدید رو وارد کنید:\n(مثال: -1001234567890)")

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
            text += f"{i}. {channel['name']}\n{channel['link']}\n\n"
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
                await callback.message.edit_text("️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
                return
        except:
            await callback.message.edit_text("⚠️ باید در کانال عضو باشی.", reply_markup=join_channel_keyboard())
            return
    if has_user_sent(user_id):
        await callback.message.edit_text("️ شما در طول روز یک بار می‌توانید پیام ارسال کنید!", reply_markup=back_menu_keyboard())
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_anonymous)
    await callback.message.edit_text(f" موضوع امروز: {topic}\n\n پیام ناشناس\n\nپیام متنی خودتون رو ارسال کنید\nاین پیام بدون یوزرنیم شما فوروارد می‌شه🙏\n\n🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n⚠️ برای انصراف دکمه پایین رو بزن.", reply_markup=back_menu_keyboard())

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
        await callback.message.edit_text("⚠️ شما در طول روز یک بار می‌توانید پیام ارسال کنید!", reply_markup=back_menu_keyboard())
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_identified)
    await callback.message.edit_text(f"📰 موضوع امروز: {topic}\n\n👤 پیام با هویت\n\nپیام متنی خودتون رو ارسال کنید\nاین پیام با یوزرنیم شما فوروارد می‌شه😄\n\n🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n️ برای انصراف دکمه پایین رو بزن.", reply_markup=back_menu_keyboard())

@dp.message(UserState.waiting_anonymous)
async def receive_anonymous(message: Message, state: FSMContext):
    if not message.text:
        return
    user_id = message.from_user.id
    add_user_to_sent(user_id)
    mark_user_participated(user_id)
    admin_id = int(ADMIN_ID)
    user_info = format_user_info(message.from_user)
    await bot.send_message(chat_id=admin_id, text=user_info)
    await bot.send_message(chat_id=admin_id, text="📩 پیام ناشناس جدید:")
    await bot.send_chat_action(chat_id=admin_id, action=ChatAction.TYPING)
    await asyncio.sleep(1.5)
    await bot.send_message(chat_id=admin_id, text=message.text)
    await message.answer("✅ پیام شما با موفقیت به دست ادمین رسید مرسی❤️\n\nحالا می‌توانید از منو، کانفیگ یا پروکسی دریافت کنید!", reply_markup=back_menu_keyboard())
    await state.clear()

@dp.message(UserState.waiting_identified)
async def receive_identified(message: Message, state: FSMContext):
    if not message.text:
        return
    user_id = message.from_user.id
    add_user_to_sent(user_id)
    mark_user_participated(user_id)
    user = message.from_user
    username = user.username
    full_name = user.full_name or "کاربر"
    signature = f"@{username}" if username else full_name
    admin_id = int(ADMIN_ID)
    user_info = format_user_info(user)
    await bot.send_message(chat_id=admin_id, text=user_info)
    combined_text = f"👤 پیام با هویت:\n\n{message.text}\n\n— {signature}"
    await bot.send_message(chat_id=admin_id, text=combined_text)
    await message.answer("✅ پیام شما با موفقیت به دست ادمین رسید مرسی❤️\n\nحالا می‌توانید از منو، کانفیگ یا پروکسی دریافت کنید!", reply_markup=back_menu_keyboard())
    await state.clear()

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if str(user_id) == ADMIN_ID:
        await callback.message.edit_text("⚙️ پنل مدیریت:", reply_markup=admin_panel_keyboard())
    else:
        await send_panel(callback, user_id, edit=True)

@dp.channel_post()
async def channel_post_handler(message: Message):
    text = message.text or ""
    logging.info(f"پیام کانال دریافت شد: {text}")
    if text.startswith("📌"):
        topic = text.replace("📌", "").strip()
        if topic:
            save_topic(topic)
            clear_sent_users()
            save_user_participation({})
            admin_id = int(ADMIN_ID)
            await bot.send_message(chat_id=admin_id, text=f"✅ موضوع روز بروزرسانی شد:\n\n📰 {topic}\n\n🗑️ لیست کاربران و مشارکت‌ها پاک شد.")

@dp.message(Command("send"))
async def send_to_user(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ فرمت صحیح:\n/send [user_id] [message]\n\nمثال:\n/send 123456789 سلام!")
        return
    try:
        user_id = int(args[1])
        user_message = args[2]
        await bot.send_message(user_id, f"📩 پیام از ادمین:\n\n{user_message}")
        await message.answer(f"✅ پیام به کاربر {user_id} ارسال شد!")
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}\n\nنکته: کاربر باید قبلاً با ربات استارت کرده باشد.")

@dp.message(Command("user"))
async def get_user_info(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ فرمت صحیح:\n/user [user_id]\n\nمثال:\n/user 123456789")
        return
    try:
        user_id = int(args[1])
        participated = has_user_participated(user_id)
        sent_message = has_user_sent(user_id)
        config_data = load_config_access()
        last_config = config_data.get(str(user_id), {}).get("last_access", "هرگز")
        proxy_data = load_proxy_access()
        last_proxy = proxy_data.get(str(user_id), {}).get("last_access", "هرگز")
        referral_count = get_referral_count(user_id)
        text = f"👤 <b>اطلاعات کاربر: {user_id}</b>\n\n📩 پیام فرستاده: {'✅ بله' if sent_message else '❌ خیر'}\n💬 مشارکت در موضوع: {'✅ بله' if participated else '❌ خیر'}\n🎁 آخرین دریافت کانفیگ: {last_config}\n🎁 آخرین دریافت پروکسی: {last_proxy}\n👥 تعداد دعوت‌ها: {referral_count}\n\n💡 <b>ارسال پیام به کاربر:</b>\n/send {user_id} [پیام شما]"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}")

@dp.message(Command("users"))
async def list_all_users(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        sent_users = load_sent_users()
        participation = load_user_participation()
        config_access = load_config_access()
        proxy_access = load_proxy_access()
        all_user_ids = set()
        all_user_ids.update(sent_users)
        all_user_ids.update(participation.keys())
        all_user_ids.update(config_access.keys())
        all_user_ids.update(proxy_access.keys())
        if not all_user_ids:
            await message.answer(" هیچ کاربری ثبت نشده است!")
            return
        text = f"👥 <b>لیست کاربران ({len(all_user_ids)} نفر):</b>\n\n"
        for user_id in sorted(all_user_ids, key=int):
            participated = "✅" if str(user_id) in participation else "❌"
            text += f"• {user_id} (مشارکت: {participated})\n"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}")

async def main():
    logging.info("Bot is starting on Server...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
