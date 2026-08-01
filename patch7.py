import shutil, py_compile, sys
SRC = "bot py.py"
BAK = SRC + ".prepatch7.bak"
shutil.copy(SRC, BAK)
s = open(SRC, encoding="utf-8").read()

REPS = [
# R1: import html
('''import importlib.util''',
 '''import importlib.util
import html'''),

# R2: promo_state funcs + verify_referrals(+bonus)
('''async def verify_referrals(user_id):
    return get_referral_count(user_id)''',
 '''PROMO_STATE_FILE = "promo_state.json"

def load_promo_state():
    try:
        return json.load(open(PROMO_STATE_FILE, encoding="utf-8"))
    except Exception:
        return {"topic_seq": 0, "promo_interval": 2, "users": {}}

def save_promo_state(d):
    json.dump(d, open(PROMO_STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)

def get_topic_seq():
    return load_promo_state().get("topic_seq", 0)

def bump_topic_seq():
    d = load_promo_state()
    d["topic_seq"] = d.get("topic_seq", 0) + 1
    save_promo_state(d)
    return d["topic_seq"]

def get_promo_interval():
    return load_promo_state().get("promo_interval", 2)

def get_promo_bonus(uid):
    return load_promo_state().get("users", {}).get(str(uid), {}).get("bonus", 0)

def should_show_promo(uid):
    d = load_promo_state()
    u = d.get("users", {}).get(str(uid), {})
    last = u.get("last_seq", -999999)
    seq = d.get("topic_seq", 0)
    interval = d.get("promo_interval", 2)
    return (seq - last) >= interval

def record_promo_done(uid):
    d = load_promo_state()
    uid = str(uid)
    d.setdefault("users", {})
    u = d["users"].setdefault(uid, {})
    u["last_seq"] = d.get("topic_seq", 0)
    u["bonus"] = u.get("bonus", 0) + 1
    save_promo_state(d)

async def _promo_gate(callback, cont_data):
    uid = str(callback.from_user.id)
    if uid == ADMIN_ID:
        return False
    if not is_promo_enabled():
        return False
    chans = get_promo_channels()
    if not chans:
        return False
    if not should_show_promo(uid):
        return False
    seq = get_topic_seq()
    ch = chans[seq % len(chans)]
    name = html.escape(str(ch.get("name", "کانال تبلیغاتی")))
    link = str(ch.get("link", ""))
    text = (f"📢 <b>تبلیغ ویژه</b>\\n\\n"
            f"قبل از ارسال نظر، لطفاً در کانال زیر عضو شو و بعد «✅ انجام دادم» را بزن.\\n\\n"
            f"🎁 با این کار یک امتیاز bonus می‌گیری که کنار دعوت‌ها در نصاب پروکسی/کانفیگ شمرده می‌شود.\\n\\n"
            f"🔗 <b>{name}</b>")
    rows = []
    if link:
        rows.append([InlineKeyboardButton(text=f"📣 عضویت در {name}", url=link)])
    rows.append([InlineKeyboardButton(text="✅ انجام دادم", callback_data=cont_data)])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    return True

async def verify_referrals(user_id):
    return get_referral_count(user_id) + get_promo_bonus(str(user_id))'''),

# R3: gate before anon form
('''    topic = load_topic()
    await state.set_state(UserState.waiting_anonymous)''',
 '''    if await _promo_gate(callback, "promo_cont_anon"):
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_anonymous)'''),

# R4: gate before id form
('''    topic = load_topic()
    await state.set_state(UserState.waiting_identified)''',
 '''    if await _promo_gate(callback, "promo_cont_id"):
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_identified)'''),

# R5: bump topic_seq on pinned post
('''        if topic:
            save_topic(topic)
            clear_sent_users()''',
 '''        if topic:
            save_topic(topic)
            bump_topic_seq()
            clear_sent_users()'''),

# 5a: add bonus/total in referral_menu
('''    count = get_referral_count(user_id)
    req_proxy = get_required_referrals()
    req_config = get_required_referrals_config()
    link = await get_or_create_ref_link(user_id)''',
 '''    count = get_referral_count(user_id)
    bonus = get_promo_bonus(str(user_id))
    total = count + bonus
    req_proxy = get_required_referrals()
    req_config = get_required_referrals_config()
    link = await get_or_create_ref_link(user_id)'''),

# 5b
('''{count}/{req_proxy}''', '''{total}/{req_proxy}'''),
# 5c
('''{count}/{req_config}''', '''{total}/{req_config}'''),
# 5d: show bonus+total lines
('''<b>{count}</b>\\n"''',
 '''<b>{count}</b>\\n"
            f"📢 امتیاز تبلیغ: <b>{bonus}</b>\\n"
            f"🧮 مجموع: <b>{total}</b>\\n"'''),
# 5e: hint line at end
('''\\n<code>{link}</code>")''',
 '''\\n<code>{link}</code>\\n\\n"
            f"💡 راه دیگر امتیاز: هنگام ارسال نظر، در کانال تبلیغاتی عضو شو.")'''),

# R7: promo_cont handlers before back_menu
('''@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):''',
 '''@dp.callback_query(F.data == "promo_cont_anon")
async def promo_cont_anon(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    record_promo_done(user_id)
    await callback.answer("✅ ممنون! امتیاز تبلیغ ثبت شد.")
    if has_user_sent(user_id):
        await callback.message.edit_text("⚠️ شما امروز یک بار نظر داده‌اید.", reply_markup=back_menu_keyboard())
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_anonymous)
    await callback.message.edit_text(f"📰 موضوع امروز: {topic}\\n\\n✍️ پیام ناشناس خود را یک‌جا بفرست (بدون یوزرنیم فوروارد می‌شود).\\n\\nبرای انصراف: 🔙", reply_markup=back_menu_keyboard())

@dp.callback_query(F.data == "promo_cont_id")
async def promo_cont_id(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    record_promo_done(user_id)
    await callback.answer("✅ ممنون! امتیاز تبلیغ ثبت شد.")
    if has_user_sent(user_id):
        await callback.message.edit_text("⚠️ شما امروز یک بار نظر داده‌اید.", reply_markup=back_menu_keyboard())
        return
    topic = load_topic()
    await state.set_state(UserState.waiting_identified)
    await callback.message.edit_text(f"📰 موضوع امروز: {topic}\\n\\n✍️ پیام با هویت خود را یک‌جا بفرست (با یوزرنیم فوروارد می‌شود).\\n\\nبرای انصراف: 🔙", reply_markup=back_menu_keyboard())

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):'''),
]

for i, (o, n) in enumerate(REPS, 1):
    c = s.count(o)
    if c != 1:
        print(f"ANCHOR {i} FAIL count={c}; file untouched (backup={BAK})")
        sys.exit(1)
    s = s.replace(o, n, 1)

open(SRC, "w", encoding="utf-8").write(s)
try:
    py_compile.compile(SRC, doraise=True)
except py_compile.PyCompileError as e:
    print("COMPILE FAIL -> restore backup"); shutil.copy(BAK, SRC); sys.exit(1)
print("PATCH7_OK applied", len(REPS), "changes")
