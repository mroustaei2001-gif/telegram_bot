import os
import logging
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

load_dotenv()

# ═══════════════════════════════════════════════
#                    تنظیمات
# ═══════════════════════════════════════════════
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# State ها
(
    WAITING_ANONYMOUS_MSG,
    WAITING_IDENTIFIED_MSG,
    WAITING_IDEA_MSG,
    ADMIN_WAITING_NEW_CHANNEL,
    ADMIN_WAITING_NEW_PROXY,
    ADMIN_WAITING_NEW_AD_CHANNEL,
    ADMIN_WAITING_REMOVE_AD
) = range(10)

# ═══════════════════════════════════════════════
#                  دیتابیس (SQLite)
# ═══════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        joined_at TIMESTAMP,
        last_proxy_time TIMESTAMP,
        last_config_time TIMESTAMP,
        referred_count INTEGER DEFAULT 0,
        has_commented_today INTEGER DEFAULT 0,
        last_comment_date TEXT,
        referrer_id INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_topic (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        topic_text TEXT,
        updated_at TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ads_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        channel_username TEXT,
        is_active INTEGER DEFAULT 1,
        added_at TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        idea_text TEXT,
        created_at TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS proxies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proxy_text TEXT,
        is_used INTEGER DEFAULT 0,
        added_at TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        config_text TEXT,
        is_used INTEGER DEFAULT 0,
        added_at TIMESTAMP
    )''')
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mandatory_join', '1')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('main_channel_id', '')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('main_channel_username', '')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('proxy_enabled', '1')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('config_enabled', '1')")
    
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def upsert_user(user_id, username, first_name, last_name, referrer_id=None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if c.fetchone():
        c.execute('''UPDATE users SET username=?, first_name=?, last_name=?
                     WHERE user_id=?''', (username, first_name, last_name, user_id))
    else:
        c.execute('''INSERT INTO users (user_id, username, first_name, last_name,
                     joined_at, referrer_id) VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, username, first_name, last_name, datetime.now(), referrer_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_all_users():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY joined_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_topic():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT topic_text FROM daily_topic WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_topic_db(text):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO daily_topic (id, topic_text, updated_at)
                 VALUES (1, ?, ?)''', (text, datetime.now()))
    conn.commit()
    conn.close()

def update_proxy_time(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE users SET last_proxy_time = ? WHERE user_id = ?',
              (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def update_config_time(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE users SET last_config_time = ? WHERE user_id = ?',
              (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def reset_comment_if_new_day(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute('SELECT last_comment_date FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row and row[0] != today:
        c.execute('''UPDATE users SET has_commented_today = 0, last_comment_date = ?
                     WHERE user_id = ?''', (today, user_id))
    conn.commit()
    conn.close()

def mark_commented_today(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute('''UPDATE users SET has_commented_today = 1, last_comment_date = ?
                 WHERE user_id = ?''', (today, user_id))
    conn.commit()
    conn.close()

def has_commented_today(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    reset_comment_if_new_day(user_id)
    c.execute('SELECT has_commented_today FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def get_referred_count(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT referred_count FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_referral(referrer_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE users SET referred_count = referred_count + 1 WHERE user_id = ?',
              (referrer_id,))
    conn.commit()
    conn.close()

def consume_referrals(user_id, count):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE users SET referred_count = MAX(0, referred_count - ?) WHERE user_id = ?',
              (count, user_id))
    conn.commit()
    conn.close()

def add_idea(user_id, text):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO ideas (user_id, idea_text, created_at) VALUES (?, ?, ?)',
              (user_id, text, datetime.now()))
    conn.commit()
    conn.close()

def get_all_ideas():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''SELECT i.id, i.user_id, i.idea_text, i.created_at, 
                 u.username, u.first_name, u.last_name 
                 FROM ideas i LEFT JOIN users u ON i.user_id = u.user_id
                 ORDER BY i.created_at DESC''')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_idea(idea_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM ideas WHERE id = ?', (idea_id,))
    conn.commit()
    conn.close()

def add_ads_channel(channel_id, channel_username):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO ads_channels (channel_id, channel_username, added_at) VALUES (?, ?, ?)',
              (channel_id, channel_username, datetime.now()))
    conn.commit()
    conn.close()

def get_all_ads_channels():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM ads_channels ORDER BY added_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_ads_channel(channel_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM ads_channels WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

def toggle_ads_channel(channel_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE ads_channels SET is_active = NOT is_active WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

def add_proxy(proxy_text):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO proxies (proxy_text, added_at) VALUES (?, ?)',
              (proxy_text, datetime.now()))
    conn.commit()
    conn.close()

def get_available_proxy():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT id, proxy_text FROM proxies WHERE is_used = 0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def mark_proxy_used(proxy_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE proxies SET is_used = 1 WHERE id = ?', (proxy_id,))
    conn.commit()
    conn.close()

def get_proxies_count():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM proxies WHERE is_used = 0')
    count = c.fetchone()[0]
    conn.close()
    return count

def add_config(config_text):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO configs (config_text, added_at) VALUES (?, ?)',
              (config_text, datetime.now()))
    conn.commit()
    conn.close()

def get_available_config():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT id, config_text FROM configs WHERE is_used = 0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def mark_config_used(config_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('UPDATE configs SET is_used = 1 WHERE id = ?', (config_id,))
    conn.commit()
    conn.close()

def get_configs_count():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM configs WHERE is_used = 0')
    count = c.fetchone()[0]
    conn.close()
    return count

# ═══════════════════════════════════════════════
#                    لاگ
# ═══════════════════════════════════════════════
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
#                  کیبوردها
# ═══════════════════════════════════════════════
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی موضوع", callback_data="refresh")],
        [InlineKeyboardButton("📩 پیام ناشناس", callback_data="anon_msg")],
        [InlineKeyboardButton("👤 پیام با هویت", callback_data="id_msg")],
        [InlineKeyboardButton("💡 ایده موضوع روز", callback_data="idea")],
        [InlineKeyboardButton("🎁 پروکسی هدیه", callback_data="proxy")],
        [InlineKeyboardButton("📦 کانفیگ 500 مگ", callback_data="config")],
        [InlineKeyboardButton("📜 قوانین و معرفی", callback_data="rules")],
        [InlineKeyboardButton("🔗 دعوت دوستان", callback_data="invite")],
    ]
    return InlineKeyboardMarkup(keyboard)

def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ انصراف", callback_data="cancel")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")]
    ])

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("💡 لیست ایده‌ها", callback_data="admin_ideas")],
        [InlineKeyboardButton("📢 مدیریت تبلیغات", callback_data="admin_ads")],
        [InlineKeyboardButton("🔒 عضویت اجباری", callback_data="admin_mandatory")],
        [InlineKeyboardButton("🎁 مدیریت پروکسی", callback_data="admin_proxy")],
        [InlineKeyboardButton("📦 مدیریت کانفیگ", callback_data="admin_config")],
        [InlineKeyboardButton("📡 تغییر کانال اصلی", callback_data="admin_channel")],
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بستن پنل", callback_data="admin_close")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ═══════════════════════════════════════════════
#                  توابع کمکی
# ═══════════════════════════════════════════════
async def check_membership(user_id, context):
    """بررسی عضویت فقط در کانال اصلی (ربات باید ادمین باشد)"""
    mandatory = get_setting('mandatory_join')
    if mandatory != '1':
        return True
    
    main_channel = get_setting('main_channel_id')
    if main_channel:
        try:
            member = await context.bot.get_chat_member(main_channel, user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
                return False
        except Exception as e:
            logger.error(f"Main channel check error: {e}")
            return False
    
    return True

async def get_join_message(context):
    """ساخت پیام عضویت - کانال اصلی اجباری، تبلیغاتی فقط لینک"""
    main_channel = get_setting('main_channel_username')
    ads_channels = get_all_ads_channels()
    
    messages = []
    
    if main_channel:
        messages.append(f"📢 *کانال اصلی (اجباری):* @{main_channel}")
    
    if ads_channels:
        messages.append("\n🎁 *کانال‌های هدیه (اختیاری):*")
        for channel in ads_channels:
            if channel[3]:  # is_active
                messages.append(f"  • @{channel[2]}")
    
    if not messages:
        return "⚠️ هیچ کانالی تنظیم نشده است."
    
    channels_text = "\n".join(messages)
    return (
        f"⚠️ برای استفاده از ربات، ابتدا باید در کانال اصلی عضو شوید:\n\n"
        f"{channels_text}\n\n"
        f"پس از عضویت، دکمه زیر را بزنید:"
    )

def get_topic_display():
    topic = get_topic()
    if not topic:
        return "📌 موضوع امروز هنوز تنظیم نشده است."
    return f"📌 *موضوع امروز:*\n\n{topic}"

def get_user_display(user_row):
    if not user_row:
        return "ناشناس"
    user_id, username, first_name, last_name = user_row[:4]
    parts = [p for p in [first_name, last_name] if p]
    name = " ".join(parts) if parts else "کاربر"
    if username:
        return f"{name} (@{username}) | ID: `{user_id}`"
    return f"{name} | ID: `{user_id}`"

def is_admin(user_id):
    return user_id == ADMIN_ID

# ═══════════════════════════════════════════════
#             هندلر /start و منوی اصلی
# ═══════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    referrer_id = None
    if args and args[0].startswith('ref_'):
        try:
            ref_id = int(args[0].split('_')[1])
            if ref_id != user.id:
                referrer_id = ref_id
        except:
            pass

    upsert_user(user.id, user.username, user.first_name, user.last_name, referrer_id)

    if not await check_membership(user.id, context):
        join_msg = await get_join_message(context)
        await update.message.reply_text(
            join_msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
            ])
        )
        return

    if referrer_id:
        referrer = get_user(referrer_id)
        if referrer:
            add_referral(referrer_id)
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🎉 یک نفر از طریق لینک دعوت شما عضو ربات شد!\n"
                    f"تعداد دعوت‌های فعلی شما: {get_referred_count(referrer_id)}"
                )
            except:
                pass

    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = (
        f"👋 خوش آمدید به کانال خودتون❤️\n"
        f"مارو به دوستاتون معرفی کنید!\n\n"
        f"{get_topic_display()}"
    )
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=main_menu_keyboard(), parse_mode='Markdown'
        )
    else:
        await update.effective_message.reply_text(
            text, reply_markup=main_menu_keyboard(), parse_mode='Markdown'
        )

# ═══════════════════════════════════════════════
#          هندلر دکمه‌های شیشه‌ای (Inline)
# ═══════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    if data not in ["cancel", "check_join", "back_to_menu"] and not data.startswith("admin_"):
        if not await check_membership(user.id, context):
            join_msg = await get_join_message(context)
            await query.edit_message_text(
                join_msg,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
                ])
            )
            return

    if data == "check_join":
        if await check_membership(user.id, context):
            await show_main_menu(update, context, edit=True)
        else:
            await query.answer("هنوز عضو نشده‌اید!", show_alert=True)
        return

    if data == "refresh":
        await show_main_menu(update, context, edit=True)
        return

    if data == "rules":
        rules_text = (
            "درباره ما\n\n"
            "به کانال \"حرفِ‌تو\" خوش آمدید!\n\n"
            "🌐 ما فضایی برای بیان آزادانه نظرات و ایده‌های شما هستیم.\n\n"
            "💚 هر روز:\n"
            "• موضوع روز برای بحث و گفتگو\n"
            "• کانفیگ 500 مگابایت رایگان\n"
            "• پروکسی‌های پرسرعت هدیه\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📜 قوانین ارسال متن\n\n"
            "پیام شما پس از ارسال به دست ادمین کانال می‌رسد\n"
            "لذا موارد زیر اگر رعایت نشود پیام شما فوروارد نخواهد شد!\n\n"
            "1️⃣ بی‌ادبی و توهین\n"
            "2️⃣ سیاسی\n"
            "3️⃣ نداشتن ارتباط با موضوع روز کانال\n"
            "4️⃣ داشتن لینک و یا موارد تبلیغاتی\n"
            "5️⃣ اسپم و فلود\n\n"
            "🤝 با ما همراه باشید!"
        )
        await query.edit_message_text(rules_text, reply_markup=back_keyboard())
        return

    if data == "invite":
        bot_user = await context.bot.get_me()
        invite_link = f"https://t.me/{bot_user.username}?start=ref_{user.id}"
        await query.edit_message_text(
            f"🔗 *لینک دعوت اختصاصی شما:*\n\n`{invite_link}`\n\n"
            f"با اشتراک‌گذاری این لینک، دوستانتان را دعوت کنید!\n"
            f"🎁 با دعوت هر نفر، امتیاز دریافت کنید و پروکسی/کانفیگ بیشتر بگیرید.\n\n"
            f"📊 تعداد دعوت‌های فعلی شما: {get_referred_count(user.id)}",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return

    if data == "anon_msg":
        context.user_data['state'] = WAITING_ANONYMOUS_MSG
        topic = get_topic() or "(تنظیم نشده)"
        await query.edit_message_text(
            f"📌 موضوع امروز:\n\n{topic}\n\n"
            f"📩 *پیام ناشناس*\n\n"
            f"پیام متنی خودتون رو ارسال کنید\n"
            f"این پیام بدون یوزرنیم شما فوروارد می‌شه🙏\n\n"
            f"🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n"
            f"⚠️ برای انصراف دکمه پایین رو بزن.",
            parse_mode='Markdown',
            reply_markup=cancel_keyboard()
        )
        return

    if data == "id_msg":
        context.user_data['state'] = WAITING_IDENTIFIED_MSG
        topic = get_topic() or "(تنظیم نشده)"
        await query.edit_message_text(
            f"📌 موضوع امروز:\n\n{topic}\n\n"
            f"👤 *پیام با هویت*\n\n"
            f"پیام متنی خودتون رو ارسال کنید\n"
            f"این پیام با یوزرنیم شما فوروارد می‌شه😄\n\n"
            f"🛡️ توجه: پیام خودتون رو به صورت کامل و بدون کات یک جا بفرستید.🫠🙏\n\n"
            f"⚠️ برای انصراف دکمه پایین رو بزن.",
            parse_mode='Markdown',
            reply_markup=cancel_keyboard()
        )
        return

    if data == "idea":
        context.user_data['state'] = WAITING_IDEA_MSG
        await query.edit_message_text(
            "💡 *ایده موضوع روز*\n\n"
            "ایده یا موضوع پیشنهادی خود را ارسال کنید.\n"
            "ما ایده‌های برتر را در کانال قرار می‌دهیم!\n\n"
            "⚠️ برای انصراف دکمه پایین رو بزن.",
            parse_mode='Markdown',
            reply_markup=cancel_keyboard()
        )
        return

    if data == "cancel":
        context.user_data.pop('state', None)
        await show_main_menu(update, context, edit=True)
        return

    if data == "proxy":
        await handle_proxy_request(update, context)
        return

    if data == "config":
        await handle_config_request(update, context)
        return

    if data.startswith("admin_"):
        await admin_handler(update, context)
        return

# ═══════════════════════════════════════════════
#          منطق پروکسی و کانفیگ
# ═══════════════════════════════════════════════
async def handle_proxy_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if get_setting('proxy_enabled') != '1':
        await query.edit_message_text(
            "⚠️ پروکسی هدیه در حال حاضر غیرفعال است.\n\n"
            "لطفاً بعداً مراجعه کنید.",
            reply_markup=back_keyboard()
        )
        return

    if not has_commented_today(user_id):
        await query.edit_message_text(
            "⚠️ برای دریافت پروکسی، ابتدا باید در موضوع روز نظر بدهید!\n\n"
            "لطفاً از منوی اصلی، گزینه '📩 پیام ناشناس' یا '👤 پیام با هویت' را انتخاب کنید "
            "و نظر خود را درباره موضوع روز بنویسید.\n\n"
            "پس از ارسال نظر، می‌توانید پروکسی رایگان دریافت کنید! 💚",
            reply_markup=back_keyboard()
        )
        return

    user = get_user(user_id)
    last_proxy = user[5]
    now = datetime.now()

    can_get_free = False
    if not last_proxy:
        can_get_free = True
    else:
        last_time = datetime.fromisoformat(last_proxy)
        if now - last_time >= timedelta(hours=24):
            can_get_free = True

    if can_get_free:
        proxy = get_available_proxy()
        if not proxy:
            await query.edit_message_text(
                "⚠️ متأسفانه پروکسی موجودی باقی نمانده است.\n\n"
                "لطفاً بعداً مراجعه کنید.",
                reply_markup=back_keyboard()
            )
            return
        
        mark_proxy_used(proxy[0])
        update_proxy_time(user_id)
        await query.edit_message_text(
            f"🎁 *پروکسی هدیه شما:*\n\n`{proxy[1]}`",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return

    referred = get_referred_count(user_id)
    if referred >= 2:
        proxy = get_available_proxy()
        if not proxy:
            await query.edit_message_text(
                "⚠️ متأسفانه پروکسی موجودی باقی نمانده است.",
                reply_markup=back_keyboard()
            )
            return
        
        consume_referrals(user_id, 2)
        mark_proxy_used(proxy[0])
        update_proxy_time(user_id)
        await query.edit_message_text(
            f"🎁 *پروکسی هدیه شما (با دعوت دوستان):*\n\n`{proxy[1]}`",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
    else:
        needed = 2 - referred
        bot_user = await context.bot.get_me()
        invite_link = f"https://t.me/{bot_user.username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"⚠️ شما در ۲۴ ساعت گذشته پروکسی دریافت کرده‌اید.\n\n"
            f"برای دریافت پروکسی بیشتر، باید *{needed} نفر* دیگر را دعوت کنید.\n\n"
            f"🔗 لینک دعوت شما:\n`{invite_link}`\n\n"
            f"📊 تعداد دعوت‌های فعلی: {referred}/2",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )

async def handle_config_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if get_setting('config_enabled') != '1':
        await query.edit_message_text(
            "⚠️ کانفیگ در حال حاضر غیرفعال است.\n\n"
            "لطفاً بعداً مراجعه کنید.",
            reply_markup=back_keyboard()
        )
        return

    if not has_commented_today(user_id):
        await query.edit_message_text(
            "⚠️ برای دریافت کانفیگ، ابتدا باید در موضوع روز نظر بدهید!\n\n"
            "لطفاً از منوی اصلی، گزینه '📩 پیام ناشناس' یا '👤 پیام با هویت' را انتخاب کنید "
            "و نظر خود را درباره موضوع روز بنویسید.\n\n"
            "پس از ارسال نظر، می‌توانید کانفیگ رایگان دریافت کنید!",
            reply_markup=back_keyboard()
        )
        return

    user = get_user(user_id)
    last_config = user[6]
    now = datetime.now()

    can_get_free = False
    if not last_config:
        can_get_free = True
    else:
        last_time = datetime.fromisoformat(last_config)
        if now - last_time >= timedelta(hours=24):
            can_get_free = True

    if can_get_free:
        config = get_available_config()
        if not config:
            await query.edit_message_text(
                "⚠️ متأسفانه کانفیگ موجودی باقی نمانده است.\n\n"
                "لطفاً بعداً مراجعه کنید.",
                reply_markup=back_keyboard()
            )
            return
        
        mark_config_used(config[0])
        update_config_time(user_id)
        await query.edit_message_text(
            f"📦 *کانفیگ 500 مگ شما:*\n\n`{config[1]}`",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
        return

    referred = get_referred_count(user_id)
    if referred >= 4:
        config = get_available_config()
        if not config:
            await query.edit_message_text(
                "⚠️ متأسفانه کانفیگ موجودی باقی نمانده است.",
                reply_markup=back_keyboard()
            )
            return
        
        consume_referrals(user_id, 4)
        mark_config_used(config[0])
        update_config_time(user_id)
        await query.edit_message_text(
            f"📦 *کانفیگ 500 مگ شما (با دعوت دوستان):*\n\n`{config[1]}`",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
    else:
        needed = 4 - referred
        bot_user = await context.bot.get_me()
        invite_link = f"https://t.me/{bot_user.username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"⚠️ شما در ۲۴ ساعت گذشته کانفیگ دریافت کرده‌اید.\n\n"
            f"برای دریافت کانفیگ بیشتر، باید *{needed} نفر* دیگر را دعوت کنید.\n\n"
            f"🔗 لینک دعوت شما:\n`{invite_link}`\n\n"
            f"📊 تعداد دعوت‌های فعلی: {referred}/4",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )

# ═══════════════════════════════════════════════
#         هندلر پیام‌های متنی کاربران
# ═══════════════════════════════════════════════
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get('state')

    if not state:
        return

    upsert_user(user.id, user.username, user.first_name, user.last_name)
    text = update.message.text or update.message.caption or ""

    if state == WAITING_ANONYMOUS_MSG:
        context.user_data.pop('state', None)
        user_info = f"📩 *پیام ناشناس*\n🆔 ID کاربر: `{user.id}`"
        if user.username:
            user_info += f"\n🔗 یوزرنیم: @{user.username}"
        user_info += f"\n👤 نام: {user.first_name or ''} {user.last_name or ''}".strip()

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"{user_info}\n\n"
                f"📌 *موضوع:* {get_topic() or '(تنظیم نشده)'}\n\n"
                f"💬 *پیام:*\n{text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send to admin: {e}")

        mark_commented_today(user.id)
        await update.message.reply_text(
            "✅ پیام شما با موفقیت ارسال شد!\n\nممنون از مشارکت شما 💚",
            reply_markup=back_keyboard()
        )
        return

    if state == WAITING_IDENTIFIED_MSG:
        context.user_data.pop('state', None)
        user_display = get_user_display(get_user(user.id))

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"👤 *پیام با هویت*\nاز: {user_display}\n\n"
                f"📌 *موضوع:* {get_topic() or '(تنظیم نشده)'}\n\n"
                f"💬 *پیام:*\n{text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send to admin: {e}")

        mark_commented_today(user.id)
        await update.message.reply_text(
            "✅ پیام شما با هویت ارسال شد!\n\nممنون از مشارکت شما 💚",
            reply_markup=back_keyboard()
        )
        return

    if state == WAITING_IDEA_MSG:
        context.user_data.pop('state', None)
        add_idea(user.id, text)
        
        user_display = get_user_display(get_user(user.id))
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💡 *ایده جدید*\nاز: {user_display}\n\n📝 *ایده:*\n{text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send idea to admin: {e}")

        await update.message.reply_text(
            "✅ ایده شما ثبت شد!\n\nممنون از پیشنهاد شما 💡",
            reply_markup=back_keyboard()
        )
        return

    if state == ADMIN_WAITING_NEW_CHANNEL and is_admin(user.id):
        context.user_data.pop('state', None)
        channel_username = text.replace('@', '').replace('https://t.me/', '').strip()
        set_setting('main_channel_username', channel_username)
        set_setting('main_channel_id', f'@{channel_username}')
        
        await update.message.reply_text(
            f"✅ کانال اصلی تنظیم شد:\n\n@{channel_username}",
            reply_markup=admin_panel_keyboard()
        )
        return

    if state == ADMIN_WAITING_NEW_PROXY and is_admin(user.id):
        context.user_data.pop('state', None)
        config_mode = context.user_data.pop('config_mode', False)
        
        if config_mode:
            add_config(text)
            count = get_configs_count()
            await update.message.reply_text(
                f"✅ کانفیگ اضافه شد!\n\n📊 تعداد کانفیگ‌های موجود: {count}",
                reply_markup=admin_panel_keyboard()
            )
        else:
            add_proxy(text)
            count = get_proxies_count()
            await update.message.reply_text(
                f"✅ پروکسی اضافه شد!\n\n📊 تعداد پروکسی‌های موجود: {count}",
                reply_markup=admin_panel_keyboard()
            )
        return

    if state == ADMIN_WAITING_NEW_AD_CHANNEL and is_admin(user.id):
        context.user_data.pop('state', None)
        channel_username = text.replace('@', '').replace('https://t.me/', '').strip()
        
        # برای کانال تبلیغاتی، نیازی به ادمین بودن ربات نیست
        # فقط یوزرنیم را ذخیره می‌کنیم
        add_ads_channel(f"@{channel_username}", channel_username)
        
        await update.message.reply_text(
            f"✅ کانال تبلیغاتی اضافه شد:\n\n@{channel_username}\n\n"
            f"⚠️ توجه: لینک این کانال به کاربران نمایش داده می‌شود.",
            reply_markup=admin_panel_keyboard()
        )
        return

    if state == ADMIN_WAITING_REMOVE_AD and is_admin(user.id):
        context.user_data.pop('state', None)
        try:
            channel_id = text.strip()
            delete_ads_channel(channel_id)
            await update.message.reply_text(
                "✅ کانال تبلیغاتی حذف شد.",
                reply_markup=admin_panel_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در حذف کانال:\n\n{str(e)}",
                reply_markup=admin_panel_keyboard()
            )
        return

# ═══════════════════════════════════════════════
#            هندلر بازگشت به منو
# ═══════════════════════════════════════════════
async def back_to_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('state', None)
    context.user_data.pop('config_mode', None)
    await show_main_menu(update, context, edit=True)

# ═══════════════════════════════════════════════
#             دستورات ادمین
# ═══════════════════════════════════════════════
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ شما ادمین نیستید.")
        return
    
    await update.message.reply_text(
        "🛠️ *پنل مدیریت ادمین*\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        parse_mode='Markdown',
        reply_markup=admin_panel_keyboard()
    )

async def settopic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ شما ادمین نیستید.")
        return
    if not context.args:
        await update.message.reply_text("❗️ استفاده: /settopic <متن موضوع>")
        return
    topic = " ".join(context.args)
    set_topic_db(topic)
    await update.message.reply_text(f"✅ موضوع روز تنظیم شد:\n\n{topic}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE has_commented_today = 1')
    active_today = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(
        f"📊 *آمار ربات:*\n\n"
        f"👥 کل کاربران: {total}\n"
        f"💬 فعال امروز: {active_today}",
        parse_mode='Markdown'
    )

# ═══════════════════════════════════════════════
#          هندلر پنل ادمین (Inline)
# ═══════════════════════════════════════════════
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if not is_admin(user_id):
        await query.answer("⛔️ دسترسی غیرمجاز!", show_alert=True)
        return

    if data == "admin_close":
        await query.edit_message_text("✅ پنل مدیریت بسته شد.")
        return

    if data == "admin_users":
        users = get_all_users()
        if not users:
            await query.edit_message_text(
                "👥 هیچ کاربری ثبت نشده است.",
                reply_markup=admin_panel_keyboard()
            )
            return
        
        text = f"👥 *لیست کاربران ({len(users)} نفر):*\n\n"
        for user in users[:20]:
            user_id, username, first_name, last_name = user[:4]
            name = f"{first_name or ''} {last_name or ''}".strip() or "بدون نام"
            username_text = f"@{username}" if username else "بدون یوزرنیم"
            text += f"• {name} ({username_text}) - ID: `{user_id}`\n"
        
        if len(users) > 20:
            text += f"\n... و {len(users) - 20} کاربر دیگر"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=admin_panel_keyboard()
        )
        return

    if data == "admin_ideas":
        ideas = get_all_ideas()
        if not ideas:
            await query.edit_message_text(
                "💡 هیچ ایده‌ای ثبت نشده است.",
                reply_markup=admin_panel_keyboard()
            )
            return
        
        text = f"💡 *لیست ایده‌ها ({len(ideas)} ایده):*\n\n"
        for idea in ideas[:15]:
            idea_id, user_id, idea_text, created_at, username, first_name, last_name = idea
            name = f"{first_name or ''} {last_name or ''}".strip() or "بدون نام"
            username_text = f"@{username}" if username else "بدون یوزرنیم"
            text += f"📝 *ایده #{idea_id}*\n"
            text += f"از: {name} ({username_text}) - ID: `{user_id}`\n"
            text += f"متن: {idea_text[:100]}{'...' if len(idea_text) > 100 else ''}\n"
            text += f"تاریخ: {created_at[:16]}\n\n"
        
        if len(ideas) > 15:
            text += f"... و {len(ideas) - 15} ایده دیگر"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=admin_panel_keyboard()
        )
        return

    if data == "admin_ads":
        ads_channels = get_all_ads_channels()
        if not ads_channels:
            text = "📢 هیچ کانال تبلیغاتی ثبت نشده است.\n\n"
            text += "برای افزودن کانال تبلیغاتی، از دکمه زیر استفاده کنید:"
            keyboard = [
                [InlineKeyboardButton("➕ افزودن کانال تبلیغاتی", callback_data="admin_add_ad")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
            ]
        else:
            text = f"📢 *لیست کانال‌های تبلیغاتی ({len(ads_channels)} کانال):*\n\n"
            for channel in ads_channels:
                channel_id, _, channel_username, is_active, _ = channel
                status = "✅ فعال" if is_active else "❌ غیرفعال"
                text += f"• @{channel_username} - {status}\n"
                text += f"  ID: `{channel_id}`\n\n"
            
            text += "\nبرای مدیریت از دکمه‌های زیر استفاده کنید:"
            keyboard = [
                [InlineKeyboardButton("➕ افزودن کانال جدید", callback_data="admin_add_ad")],
                [InlineKeyboardButton("🗑️ حذف کانال", callback_data="admin_remove_ad")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
            ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "admin_add_ad":
        context.user_data['state'] = ADMIN_WAITING_NEW_AD_CHANNEL
        await query.edit_message_text(
            "📢 *افزودن کانال تبلیغاتی*\n\n"
            "لطفاً یوزرنیم کانال را ارسال کنید:\n"
            "(مثال: @channelname یا channelname)\n\n"
            "⚠️ توجه: ربات نیازی به ادمین بودن در این کانال ندارد.\n"
            "فقط لینک کانال به کاربران نمایش داده می‌شود.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="admin_ads")]
            ])
        )
        return

    if data == "admin_remove_ad":
        context.user_data['state'] = ADMIN_WAITING_REMOVE_AD
        ads_channels = get_all_ads_channels()
        text = "🗑️ *حذف کانال تبلیغاتی*\n\n"
        text += "لطفاً ID کانال مورد نظر را ارسال کنید:\n\n"
        for channel in ads_channels:
            text += f"• @{channel[2]} - ID: `{channel[1]}`\n"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="admin_ads")]
            ])
        )
        return

    if data == "admin_mandatory":
        current = get_setting('mandatory_join')
        status = "✅ فعال" if current == '1' else "❌ غیرفعال"
        main_channel = get_setting('main_channel_username')
        
        text = (
            f"🔒 *مدیریت عضویت اجباری*\n\n"
            f"وضعیت فعلی: {status}\n\n"
        )
        
        if main_channel:
            text += f"📢 کانال اصلی: @{main_channel}\n\n"
        else:
            text += "⚠️ کانال اصلی تنظیم نشده است!\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data="admin_toggle_mandatory")],
            [InlineKeyboardButton("📡 تنظیم کانال اصلی", callback_data="admin_channel")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "admin_toggle_mandatory":
        current = get_setting('mandatory_join')
        new_value = '0' if current == '1' else '1'
        set_setting('mandatory_join', new_value)
        status = "✅ فعال" if new_value == '1' else "❌ غیرفعال"
        
        await query.answer(f"عضویت اجباری {status} شد!", show_alert=True)
        await admin_handler(update, context)
        return

    if data == "admin_proxy":
        enabled = get_setting('proxy_enabled')
        status = "✅ فعال" if enabled == '1' else "❌ غیرفعال"
        count = get_proxies_count()
        
        text = (
            f"🎁 *مدیریت پروکسی هدیه*\n\n"
            f"وضعیت: {status}\n"
            f"📊 تعداد پروکسی‌های موجود: {count}\n\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data="admin_toggle_proxy")],
            [InlineKeyboardButton("➕ افزودن پروکسی", callback_data="admin_add_proxy")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "admin_toggle_proxy":
        current = get_setting('proxy_enabled')
        new_value = '0' if current == '1' else '1'
        set_setting('proxy_enabled', new_value)
        status = "✅ فعال" if new_value == '1' else "❌ غیرفعال"
        
        await query.answer(f"پروکسی {status} شد!", show_alert=True)
        await admin_handler(update, context)
        return

    if data == "admin_add_proxy":
        context.user_data['state'] = ADMIN_WAITING_NEW_PROXY
        context.user_data['config_mode'] = False
        await query.edit_message_text(
            "🎁 *افزودن پروکسی*\n\n"
            "لطفاً کانفیگ پروکسی را ارسال کنید:\n"
            "(مثال: vless://... یا vmess://...)\n\n"
            "⚠️ توجه: هر پروکسی فقط یک بار قابل دریافت است.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="admin_proxy")]
            ])
        )
        return

    if data == "admin_config":
        enabled = get_setting('config_enabled')
        status = "✅ فعال" if enabled == '1' else "❌ غیرفعال"
        count = get_configs_count()
        
        text = (
            f"📦 *مدیریت کانفیگ*\n\n"
            f"وضعیت: {status}\n"
            f"📊 تعداد کانفیگ‌های موجود: {count}\n\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data="admin_toggle_config")],
            [InlineKeyboardButton("➕ افزودن کانفیگ", callback_data="admin_add_config")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "admin_toggle_config":
        current = get_setting('config_enabled')
        new_value = '0' if current == '1' else '1'
        set_setting('config_enabled', new_value)
        status = "✅ فعال" if new_value == '1' else "❌ غیرفعال"
        
        await query.answer(f"کانفیگ {status} شد!", show_alert=True)
        await admin_handler(update, context)
        return

    if data == "admin_add_config":
        context.user_data['state'] = ADMIN_WAITING_NEW_PROXY
        context.user_data['config_mode'] = True
        await query.edit_message_text(
            "📦 *افزودن کانفیگ*\n\n"
            "لطفاً کانفیگ را ارسال کنید:\n"
            "(مثال: vless://... یا vmess://...)\n\n"
            "⚠️ توجه: هر کانفیگ فقط یک بار قابل دریافت است.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="admin_config")]
            ])
        )
        return

    if data == "admin_channel":
        current = get_setting('main_channel_username')
        text = (
            f"📡 *تغییر کانال اصلی*\n\n"
            f"کانال فعلی: "
        )
        if current:
            text += f"@{current}\n\n"
        else:
            text += "تنظیم نشده\n\n"
        
        text += "لطفاً یوزرنیم کانال جدید را ارسال کنید:\n"
        text += "(مثال: @channelname یا channelname)\n\n"
        text += "⚠️ توجه: ربات باید ادمین کانال اصلی باشد."
        
        context.user_data['state'] = ADMIN_WAITING_NEW_CHANNEL
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ انصراف", callback_data="admin_back")]
            ])
        )
        return

    if data == "admin_stats":
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users WHERE has_commented_today = 1')
        active_today = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM ideas')
        total_ideas = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM proxies WHERE is_used = 0')
        available_proxies = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM configs WHERE is_used = 0')
        available_configs = c.fetchone()[0]
        conn.close()
        
        text = (
            f"📊 *آمار کلی ربات:*\n\n"
            f"👥 کل کاربران: {total_users}\n"
            f"💬 فعال امروز: {active_today}\n"
            f"💡 کل ایده‌ها: {total_ideas}\n"
            f"🎁 پروکسی‌های موجود: {available_proxies}\n"
            f"📦 کانفیگ‌های موجود: {available_configs}\n"
        )
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=admin_panel_keyboard()
        )
        return

    if data == "admin_back":
        context.user_data.pop('state', None)
        context.user_data.pop('config_mode', None)
        await query.edit_message_text(
            "🛠️ *پنل مدیریت ادمین*\n\n"
            "از دکمه‌های زیر استفاده کنید:",
            parse_mode='Markdown',
            reply_markup=admin_panel_keyboard()
        )
        return

# ═══════════════════════════════════════════════
#                   اجرای اصلی
# ═══════════════════════════════════════════════
def main():
    if not TOKEN:
        logger.error("❌ توکن ربات یافت نشد! فایل .env را بررسی کنید.")
        return

    init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("settopic", settopic_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    application.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 ربات در حال اجرا است...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
