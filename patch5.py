import sys, shutil, py_compile
FILE = "bot py.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()
shutil.copy(FILE, FILE + ".prepatch5.bak")
errs = []
def repl(old, new, label):
    global src
    if old not in src:
        errs.append(label); return
    src = src.replace(old, new, 1); print("  ok", label)

repl('from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton',
     'from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton, ChatMemberUpdated',
     "P5-1-import")

repl('TOPIC_IDEAS_FILE = "topic_ideas.json"',
     'TOPIC_IDEAS_FILE = "topic_ideas.json"\nREF_LINKS_FILE = "ref_links.json"',
     "P5-2-reffile")
repl('def get_referral_display_channel():\n    return get_referral_base_link() or get_channel_link()',
'def get_referral_display_channel():\n    return get_referral_base_link() or get_channel_link()\n\ndef load_ref_links():\n    try:\n        with open(REF_LINKS_FILE, "r", encoding="utf-8") as f:\n            return json.load(f)\n    except Exception:\n        return {}\n\ndef save_ref_links(d):\n    with open(REF_LINKS_FILE, "w", encoding="utf-8") as f:\n        json.dump(d, f, ensure_ascii=False, indent=2)\n\ndef remove_referral(referrer_id, referred_id):\n    referrals = load_referrals()\n    key = str(referrer_id)\n    if key in referrals and str(referred_id) in referrals[key]:\n        referrals[key].remove(str(referred_id))\n        save_referrals(referrals)\n        return True\n    return False\n\nasync def get_or_create_ref_link(user_id):\n    links = load_ref_links()\n    key = str(user_id)\n    existing = links.get(key)\n    if existing:\n        return existing\n    try:\n        ch = int(get_channel_id())\n        inv = await bot.create_chat_invite_link(chat_id=ch, name=f"ref_{user_id}", member_limit=99999)\n        links[key] = inv.invite_link\n        save_ref_links(links)\n        return inv.invite_link\n    except Exception as e:\n        logging.warning("get_or_create_ref_link: %s", e)\n        bot_username = (await bot.get_me()).username\n        return f"https://t.me/{bot_username}?start=ref_{user_id}"',
     "P5-3-reflink-funcs")
repl('async def verify_referrals(user_id):\n    refs = load_referrals()\n    key = str(user_id)\n    user_refs = refs.get(key, [])\n    channel_id = get_channel_id()\n    if not channel_id or not user_refs:\n        return len(user_refs)\n    valid = 0\n    for ref_id in user_refs:\n        try:\n            member = await bot.get_chat_member(channel_id, int(ref_id))\n            if member.status in ("member", "administrator", "creator"):\n                valid += 1\n        except Exception:\n            pass\n    return valid',
'async def verify_referrals(user_id):\n    return get_referral_count(user_id)',
     "P5-4-verify-simple")

repl('    await verify_referrals(user_id)\n    count = get_referral_count(user_id)',
     '    count = get_referral_count(user_id)',
     "P5-5a-menu-noverify")

repl('    link = await build_referral_link(user_id)',
     '    link = await get_or_create_ref_link(user_id)',
     "P5-5b-menu-link")

repl('    ch = get_referral_display_channel() or "کانال (از پنل تنظیم شود)"',
     '',
     "P5-5c-menu-noch")

repl('            f"👥 وارد ربات شده: {count}\\n"\n            f"✅ عضو کانال (معتبر): <b>{valid}</b>\\n"',
'            f"✅ دعوت‌های معتبر: <b>{count}</b>\\n"',
     "P5-5d-menu-count")

repl('            f"📌 <b>به دوستت بگو:</b>\\n"\n            f"1️⃣ اول عضو کانال شو: {ch}\\n"\n            f"2️⃣ بعد روی لینک زیر بزن و /start کن:\\n"\n            f"<code>{link}</code>")',
'            f"🔗 <b>لینک دعوت شما (با آن در کانال عضو شوید):</b>\\n<code>{link}</code>")',
     "P5-5e-menu-text")
repl('async def main():\n    logging.info("Bot is starting on Server...")',
'@dp.chat_member()\nasync def on_ref_chat_member(update: ChatMemberUpdated):\n    try:\n        if str(update.chat.id) != get_channel_id():\n            return\n        inv = update.invite_link\n        if not inv or not getattr(inv, "invite_link", None):\n            return\n        link = inv.invite_link\n        links = load_ref_links()\n        referrer = None\n        for uid, lk in links.items():\n            if lk == link:\n                referrer = uid\n                break\n        if not referrer:\n            return\n        new_user = update.new_chat_member.user.id\n        old_st = update.old_chat_member.status\n        new_st = update.new_chat_member.status\n        if new_st in ("member", "administrator", "creator") and old_st in ("left", "kicked"):\n            if str(new_user) != referrer:\n                add_referral(referrer, new_user)\n                try:\n                    await bot.send_message(int(referrer), f"✅ یک نفر با لینک دعوت شما عضو کانال شد!\\nتعداد دعوت‌های معتبر: {get_referral_count(referrer)}")\n                except Exception:\n                    pass\n        elif old_st in ("member", "administrator", "creator") and new_st in ("left", "kicked"):\n            remove_referral(referrer, new_user)\n    except Exception as e:\n        logging.warning("on_ref_chat_member: %s", e)\n\nasync def main():\n    logging.info("Bot is starting on Server...")',
     "P5-6-chatmember-handler")

if errs:
    print("ERR anchors:", errs); sys.exit(1)
with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
try:
    py_compile.compile(FILE, doraise=True)
    print("PATCH5_OK")
except py_compile.PyCompileError as e:
    print("SYNTAX_ERR", e); shutil.copy(FILE + ".prepatch5.bak", FILE); sys.exit(1)
