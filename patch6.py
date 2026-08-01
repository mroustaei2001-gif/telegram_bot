import sys, shutil, py_compile
FILE = "bot py.py"
src = open(FILE, encoding="utf-8").read()
shutil.copy(FILE, FILE + ".prepatch6.bak")
errs = []
def repl(old, new, label):
    global src
    if old not in src:
        errs.append(label); return
    src = src.replace(old, new, 1); print("  ok", label)

repl('from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton',
     'from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton, ChatMemberUpdated',
     "R1-import")

repl('TOPIC_IDEAS_FILE = "topic_ideas.json"',
     'TOPIC_IDEAS_FILE = "topic_ideas.json"\nREF_LINKS_FILE = "ref_links.json"',
     "R2-const")
repl('''async def verify_referrals(user_id):
    refs = load_referrals()
    key = str(user_id)
    user_refs = refs.get(key, [])
    channel_id = get_channel_id()
    if not channel_id or not user_refs:
        return len(user_refs)
    valid = 0
    for ref_id in user_refs:
        try:
            member = await bot.get_chat_member(channel_id, int(ref_id))
            if member.status in ("member", "administrator", "creator"):
                valid += 1
        except Exception:
            pass
    return valid''',
'''async def verify_referrals(user_id):
    return get_referral_count(user_id)

def load_ref_links():
    try:
        return json.load(open(REF_LINKS_FILE, encoding="utf-8"))
    except Exception:
        return {}

def save_ref_links(d):
    json.dump(d, open(REF_LINKS_FILE, "w", encoding="utf-8"), ensure_ascii=False)

def remove_referral(a, b):
    r = load_referrals(); k = str(a)
    if k in r and str(b) in r[k]:
        r[k].remove(str(b)); save_referrals(r); return True
    return False

async def get_or_create_ref_link(uid):
    L = load_ref_links(); k = str(uid)
    if L.get(k):
        return L[k]
    inv = await bot.create_chat_invite_link(int(get_channel_id()), name=f"ref_{uid}", member_limit=99999)
    L[k] = inv.invite_link; save_ref_links(L); return inv.invite_link''',
     "R3-refs")
repl('''@dp.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    valid = await verify_referrals(user_id)
    count = get_referral_count(user_id)
    req_proxy = get_required_referrals()
    req_config = get_required_referrals_config()
    link = await build_referral_link(user_id)
    text = (f"👥 <b>دعوت دوستان</b>\\n\\n"
            f"با دعوت دوستانت، پروکسی ویژه و کانفیگ فوری بگیر!\\n\\n"
            f"👥 وارد ربات شده: {count}\\n"
            f"✅ عضو کانال (معتبر): <b>{valid}</b>\\n"
            f"🎁 پروکسی ویژه: {valid}/{req_proxy}\\n"
            f"🔑 کانفیگ فوری: {valid}/{req_config}\\n\\n"
            f"🔗 <b>لینک دعوت اختصاصی شما:</b>\\n<code>{link}</code>")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")''',
'''@dp.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = get_referral_count(user_id)
    req_proxy = get_required_referrals()
    req_config = get_required_referrals_config()
    link = await get_or_create_ref_link(user_id)
    text = (f"👥 <b>دعوت دوستان</b>\\n\\n"
            f"با دعوت دوستانت، پروکسی ویژه و کانفیگ فوری بگیر!\\n\\n"
            f"✅ دعوت‌های معتبر: <b>{count}</b>\\n"
            f"🎁 پروکسی ویژه: {count}/{req_proxy}\\n"
            f"🔑 کانفیگ فوری: {count}/{req_config}\\n\\n"
            f"🔗 <b>لینک دعوت شما (دوستت با آن عضو کانال می‌شود):</b>\\n<code>{link}</code>")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")''',
     "R4-menu")
repl('''async def main():
    logging.info("Bot is starting on Server...")''',
'''@dp.chat_member()
async def on_ref_chat_member(update: ChatMemberUpdated):
    try:
        if str(update.chat.id) != get_channel_id():
            return
        inv = update.invite_link
        if not inv or not getattr(inv, "invite_link", None):
            return
        link = inv.invite_link
        L = load_ref_links(); referrer = None
        for uid, lk in L.items():
            if lk == link:
                referrer = uid; break
        if not referrer:
            return
        nu = update.new_chat_member.user.id
        os_ = update.old_chat_member.status
        ns = update.new_chat_member.status
        if ns in ("member","administrator","creator") and os_ in ("left","kicked"):
            if str(nu) != referrer and add_referral(referrer, nu):
                try:
                    await bot.send_message(int(referrer), f"✅ یک نفر با لینک دعوت شما عضو کانال شد!\\nتعداد دعوت‌های معتبر: {get_referral_count(referrer)}")
                except Exception:
                    pass
        elif os_ in ("member","administrator","creator") and ns in ("left","kicked"):
            remove_referral(referrer, nu)
    except Exception as e:
        logging.warning("on_ref_chat_member: %s", e)

async def main():
    logging.info("Bot is starting on Server...")''',
     "R5-handler")

if errs:
    print("ERR anchors:", errs); sys.exit(1)
open(FILE, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(FILE, doraise=True); print("PATCH6_OK")
except py_compile.PyCompileError as e:
    print("SYNTAX_ERR", e); shutil.copy(FILE + ".prepatch6.bak", FILE); sys.exit(1)
