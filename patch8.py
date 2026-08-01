import shutil, py_compile, sys
SRC = "bot py.py"
BAK = SRC + ".prepatch8.bak"
shutil.copy(SRC, BAK)
s = open(SRC, encoding="utf-8").read()

REPS = [
# 1: add refresh button in referral_menu keyboard
('''        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]''',
 '''        [InlineKeyboardButton(text="📋 کپی لینک دعوت", copy_text=CopyTextButton(text=link))],
        [InlineKeyboardButton(text="🔄 به‌روزرسانی تعداد", callback_data="refresh_referral")],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]'''),

# 2: define clear_user_referrals after remove_referral
('''def remove_referral(a, b):
    r = load_referrals(); k = str(a)
    if k in r and str(b) in r[k]:
        r[k].remove(str(b)); save_referrals(r); return True
    return False''',
 '''def remove_referral(a, b):
    r = load_referrals(); k = str(a)
    if k in r and str(b) in r[k]:
        r[k].remove(str(b)); save_referrals(r); return True
    return False

def clear_user_referrals(uid):
    r = load_referrals(); k = str(uid)
    if k in r:
        r[k] = []; save_referrals(r); return True
    return False'''),

# 3: refresh_referral handler (re-uses referral_menu -> fresh numbers)
('''@dp.callback_query(F.data == "set_ref_config_count")''',
 '''@dp.callback_query(F.data == "refresh_referral")
async def refresh_referral(callback: CallbackQuery):
    await referral_menu(callback)

@dp.callback_query(F.data == "set_ref_config_count")'''),
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
print("PATCH8_OK applied", len(REPS), "changes")
