#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, shutil, sys, py_compile

FILE = "bot py.py"
BAK  = FILE + ".prepatch.bak"

with open(FILE, encoding="utf-8") as f:
    src = f.read()
shutil.copy(FILE, BAK)

errors = []
def repl(old, new, label, n=1):
    global src
    c = src.count(old)
    if c < n:
        errors.append(f"[{label}] anchor پیدا نشد (یافت={c})"); return
    src = src.replace(old, new, n); print(f"  ok {label}")

def repl_re(pattern, new, label):
    global src
    new_src, c = re.subn(pattern, lambda m: new, src, count=1, flags=re.DOTALL)
    if c < 1:
        errors.append(f"[{label}] regex پیدا نشد"); return
    src = new_src; print(f"  ok {label}")

# 1) imports
repl(
"import random\nimport requests\nfrom datetime import datetime, timedelta\nfrom aiogram import Bot, Dispatcher, F\n",
"import random\nimport uuid\nimport importlib.util\nfrom datetime import datetime, timedelta\nfrom aiogram import Bot, Dispatcher, F, BaseMiddleware\n",
"imports")

# 2) BOT_TOKEN env (fallback خالی -> توکن لو رفته از کد حذف می‌شود)
repl('BOT_TOKEN = "8916837966:AAHaYZGz2X8OsI5DuZ9_h9RAj5oVDgrhw2s"',
     'BOT_TOKEN = os.getenv("BOT_TOKEN", "")',
     "BOT_TOKEN")

# 3) ADMIN_ID env
repl('ADMIN_ID = "6282695098"',
     'ADMIN_ID = os.getenv("ADMIN_ID", "6282695098")',
     "ADMIN_ID")

# 4) حذف ثابت‌های Marzban
repl(
'MARZBAN_URL = "https://panel.shahinfree.shop"\n'
'MARZBAN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzaGFoaW4iLCJhY2Nlc3MiOiJhZG1pbiIsImlhdCI6MTc4NTMzMTU2MSwiZXhwIjoxNzg1NDE3OTYxfQ.RoO5wb6GcELmeltlbLeJvmYbHqjk9AdFa5gb60M7V6o"\n',
'',
"remove-marzban-consts")

# 5) load_settings default
repl('"required_referrals": 2, "proxy_enabled": True}',
     '"required_referrals": 2, "required_referrals_config": 4, "referral_base_link": "", "proxy_enabled": True}',
     "settings-default")

# 6) توابع جدید بعد از get_referral_count
repl(
"def get_referral_count(user_id):\n    return len(load_referrals().get(str(user_id), []))\n",
'''def get_referral_count(user_id):
    return len(load_referrals().get(str(user_id), []))

def get_referral_base_link():
    return load_settings().get("referral_base_link", "")

def set_referral_base_link(link):
    settings = load_settings()
    settings["referral_base_link"] = link
    save_settings(settings)

def get_required_referrals_config():
    return load_settings().get("required_referrals_config", 4)

def set_required_referrals_config(count):
    settings = load_settings()
    settings["required_referrals_config"] = count
    save_settings(settings)

async def build_referral_link(user_id):
    base = get_referral_base_link()
    if not base:
        bot_username = (await bot.get_me()).username
        base = f"https://t.me/{bot_username}"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}start=ref_{user_id}"

async def verify_referrals(user_id):
    refs = load_referrals()
    key = str(user_id)
    user_refs = refs.get(key, [])
    channel_id = get_channel_id()
    if not channel_id or not user_refs:
        return len(user_refs)
    valid = []
    for ref_id in user_refs:
        try:
            member = await bot.get_chat_member(channel_id, int(ref_id))
            if member.status in ("member", "administrator", "creator"):
                valid.append(ref_id)
        except Exception:
            valid.append(ref_id)
    refs[key] = valid
    save_referrals(refs)
    return len(valid)
''',
"new-referral-funcs")

# 7) حذف توابع Marzban + افزودن make_vless_config
make_vless = '''def _load_xui():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "majool")
    spec = importlib.util.spec_from_file_location("xui_db", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.XuiDB()

def make_vless_config(user_id):
    xui = _load_xui()
    email = f"tg{user_id}_{uuid.uuid4().hex[:6]}"
    link, u, e, info = xui.make_config(total_gb=500, days=1, limit_ip=1, email=email)
    return link, info
'''
repl_re(r'def get_marzban_headers\(\):.*?return f"خطا: \{res\.status_code\}"\n',
        make_vless, "replace-marzban-funcs")

# 8) can_user_get_config
repl(
"    if get_referral_count(user_id) >= 4 and not data[key].get(\"bonus_used\", False):\n        return True, 4\n",
"    if get_referral_count(user_id) >= get_required_referrals_config() and not data[key].get(\"bonus_used\", False):\n        return True, get_required_referrals_config()\n",
"config-ref-count")

# 9) main_menu_keyboard
repl(
'        [InlineKeyboardButton(text="🔑 دریافت کانفیگ 500 مگ", callback_data="get_config")],\n'
'        [InlineKeyboardButton(text="📜 قوانین و معرفی ما", callback_data="rules_and_about")],\n',
'        [InlineKeyboardButton(text="🔑 دریافت کانفیگ 500 مگ", callback_data="get_config")],\n'
'        [InlineKeyboardButton(text="👥 دعوت دوستان", callback_data="referral_menu")],\n'
'        [InlineKeyboardButton(text="📜 قوانین و معرفی ما", callback_data="rules_and_about")],\n',
"main-menu-referral")

# 10) admin_panel_keyboard
repl(
'        [InlineKeyboardButton(text=f" دعوت: {get_required_referrals()}", callback_data="set_referral_count")],\n',
'        [InlineKeyboardButton(text=f" دعوت: {get_required_referrals()}", callback_data="set_referral_count")],\n'
'        [InlineKeyboardButton(text=f"🔑 دعوت کانفیگ: {get_required_referrals_config()}", callback_data="set_ref_config_count")],\n'
'        [InlineKeyboardButton(text="🔗 لینک پایه دعوت", callback_data="set_ref_base")],\n',
"admin-panel-referral")

# 11) UserState
repl(
"    adding_channel_link_name = State()\n    adding_channel_link_url = State()\n",
"    adding_channel_link_name = State()\n    adding_channel_link_url = State()\n    setting_ref_config_count = State()\n    setting_ref_base = State()\n",
"user-states")

# 12) middleware قبل از cmd_start
middleware = '''class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        if str(user.id) == ADMIN_ID:
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == "check_join":
            return await handler(event, data)
        if not is_force_join_enabled():
            return await handler(event, data)
        channel_id = get_channel_id()
        if not channel_id:
            return await handler(event, data)
        try:
            member = await bot.get_chat_member(channel_id, user.id)
            if member.status in ("member", "administrator", "creator"):
                return await handler(event, data)
        except Exception:
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
            except Exception:
                await event.message.answer("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
            await event.answer()
        else:
            await event.answer("⚠️ برای استفاده از ربات، ابتدا باید در کانال عضو بشی.", reply_markup=join_channel_keyboard())
        return

dp.message.middleware(ForceJoinMiddleware())
dp.callback_query.middleware(ForceJoinMiddleware())

@dp.message(CommandStart())
async def cmd_start(message: Message):
'''
repl("@dp.message(CommandStart())\nasync def cmd_start(message: Message):\n",
     middleware, "force-join-middleware")

# 13) handlerهای جدید قبل از main()
new_handlers = '''@dp.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    await verify_referrals(user_id)
    count = get_referral_count(user_id)
    req_proxy = get_required_referrals()
    req_config = get_required_referrals_config()
    link = await build_referral_link(user_id)
    text = (f"👥 <b>دعوت دوستان</b>\\n\\n"
            f"با دعوت دوستانت، پروکسی ویژه و کانفیگ فوری بگیر!\\n\\n"
            f"✅ دعوت‌های معتبر: <b>{count}</b>\\n"
            f"🎁 پروکسی ویژه: {count}/{req_proxy}\\n"
            f"🔑 کانفیگ فوری: {count}/{req_config}\\n\\n"
            f"🔗 <b>لینک دعوت اختصاصی شما:</b>\\n<code>{link}</code>")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "set_ref_config_count")
async def set_ref_config_count_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    current = get_required_referrals_config()
    await state.set_state(UserState.setting_ref_config_count)
    await callback.message.edit_text(f"تعداد فعلی دعوت برای کانفیگ فوری: {current}\\n\\nعدد جدید را وارد کنید:")

@dp.message(UserState.setting_ref_config_count)
async def set_ref_config_count(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید!")
        return
    count = int(message.text)
    if count < 1:
        await message.answer("❌ عدد باید حداقل 1 باشد!")
        return
    set_required_referrals_config(count)
    await message.answer(f"✅ تعداد دعوت کانفیگ به {count} تغییر کرد!", reply_markup=admin_panel_keyboard())
    await state.clear()

@dp.callback_query(F.data == "set_ref_base")
async def set_ref_base_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    current = get_referral_base_link() or "پیش‌فرض (لینک خود ربات)"
    await state.set_state(UserState.setting_ref_base)
    await callback.message.edit_text(f"لینک پایه دعوت فعلی: {current}\\n\\nلینک جدید را وارد کنید (مثلاً https://t.me/YourBot):\\nبرای بازگشت به پیش‌فرض، فقط یک خط‌تیره بفرست: -")

@dp.message(UserState.setting_ref_base)
async def set_ref_base(message: Message, state: FSMContext):
    if not message.text:
        return
    val = message.text.strip()
    if val == "-":
        val = ""
    set_referral_base_link(val)
    await message.answer(f"✅ لینک پایه دعوت تنظیم شد: {val or 'پیش‌فرض (لینک ربات)'}", reply_markup=admin_panel_keyboard())
    await state.clear()

async def main():
    logging.info("Bot is starting on Server...")
'''
repl('async def main():\n    logging.info("Bot is starting on Server...")\n',
     new_handlers, "new-handlers")

# 14) confirm_config بخش اول
repl(
"    can_access, info = can_user_get_config(user_id)\n"
"    if not can_access:\n"
"        hours_left = info\n"
"        bot_username = (await bot.get_me()).username\n"
'        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"\n',
"    await verify_referrals(user_id)\n"
"    can_access, info = can_user_get_config(user_id)\n"
"    if not can_access:\n"
"        hours_left = info\n"
"        referral_link = await build_referral_link(user_id)\n",
"confirm-config-1")

# 15) confirm_config عدد 4 نفر
repl("اگر <b>4 نفر</b> را با لینک زیر به کانال دعوت کنید، بلافاصله یک کانفیگ دیگر دریافت می‌کنید!",
     "اگر <b>{get_required_referrals_config()} نفر</b> را با لینک زیر به کانال دعوت کنید، بلافاصله یک کانفیگ دیگر دریافت می‌کنید!",
     "confirm-config-4nafar")

# 16) confirm_config ساخت کانفیگ
repl(
"    config_link = create_or_get_config(user_id)\n"
'    if config_link.startswith("خطا"):\n'
'        await callback.message.edit_text(f"❌ {config_link}\\n\\nلطفاً بعداً مجدداً تلاش کنید یا به ادمین پیام دهید.", reply_markup=back_menu_keyboard())\n'
"        return\n"
"    referrals = get_referral_count(user_id)\n"
"    is_bonus = referrals >= 4\n"
"    record_config_access(user_id, is_bonus=is_bonus)\n"
"    bot_username = (await bot.get_me()).username\n"
'    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"\n',
"    try:\n"
"        loop = asyncio.get_running_loop()\n"
"        config_link, cfg_info = await loop.run_in_executor(None, make_vless_config, user_id)\n"
"    except Exception as e:\n"
'        await callback.message.edit_text(f"❌ خطا در ساخت کانفیگ: {e}\\n\\nلطفاً بعداً مجدداً تلاش کنید یا به ادمین پیام دهید.", reply_markup=back_menu_keyboard())\n'
"        return\n"
"    referrals = get_referral_count(user_id)\n"
"    is_bonus = referrals >= get_required_referrals_config()\n"
"    record_config_access(user_id, is_bonus=is_bonus)\n"
"    referral_link = await build_referral_link(user_id)\n",
"confirm-config-build")

# 17) confirm_proxy بخش اول
repl(
"    can_access, last_access = can_user_access_proxy(user_id)\n"
"    if not can_access:\n"
"        time_left = timedelta(days=1) - (datetime.now() - last_access)\n"
"        hours = int(time_left.total_seconds() // 3600)\n"
"        minutes = int((time_left.total_seconds() % 3600) // 60)\n"
"        bot_username = (await bot.get_me()).username\n"
'        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"\n',
"    await verify_referrals(user_id)\n"
"    can_access, last_access = can_user_access_proxy(user_id)\n"
"    if not can_access:\n"
"        time_left = timedelta(days=1) - (datetime.now() - last_access)\n"
"        hours = int(time_left.total_seconds() // 3600)\n"
"        minutes = int((time_left.total_seconds() % 3600) // 60)\n"
"        referral_link = await build_referral_link(user_id)\n",
"confirm-proxy-1")

# 18) confirm_proxy بخش دوم
repl(
"    proxy_text = random.choice(proxies)\n"
"    bot_username = (await bot.get_me()).username\n"
'    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"\n',
"    proxy_text = random.choice(proxies)\n"
"    referral_link = await build_referral_link(user_id)\n",
"confirm-proxy-2")

# 19) join_channel_keyboard (اگر لینک کانال خالی بود، دکمه url نگذارد تا خطا ندهد)
repl(
"def join_channel_keyboard():\n    channel_link = get_channel_link()\n    buttons = [[InlineKeyboardButton(text=\"📢 عضویت در کانال\", url=channel_link)]]\n",
"def join_channel_keyboard():\n    channel_link = get_channel_link()\n    buttons = []\n    if channel_link:\n        buttons.append([InlineKeyboardButton(text=\"📢 عضویت در کانال\", url=channel_link)])\n",
"join-kb-url")

# ---- نتیجه ----
if errors:
    print("\n❌ این anchorها پیدا نشدند:")
    for e in errors:
        print("   -", e)
    print("\n⛔ فایل تغییر نکرد. backup سالم است:", BAK)
    sys.exit(1)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
try:
    py_compile.compile(FILE, doraise=True)
    print("\n✅ همهٔ ۱۹ تغییر اعمال شد و syntax درست است.")
    print("✅ backup:", BAK)
except py_compile.PyCompileError as e:
    print("\n❌ syntax error:", e)
    shutil.copy(BAK, FILE)
    print("⛔ backup برگردانده شد.")
    sys.exit(1)
