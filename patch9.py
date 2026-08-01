import shutil, py_compile, sys
SRC = "bot py.py"
BAK = SRC + ".prepatch9.bak"
shutil.copy(SRC, BAK)
s = open(SRC, encoding="utf-8").read()

REPS = [
('''def clear_user_referrals(uid):
    r = load_referrals(); k = str(uid)
    if k in r:
        r[k] = []; save_referrals(r); return True
    return False''',
 '''def clear_user_referrals(uid):
    r = load_referrals(); k = str(uid)
    if k in r:
        r[k] = []; save_referrals(r); return True
    return False

def reset_user_progress(uid):
    clear_user_referrals(uid)
    d = load_promo_state(); k = str(uid)
    u = d.get("users", {}).get(k)
    if u:
        u["bonus"] = 0
        save_promo_state(d)'''),
('''    is_bonus = referrals >= get_required_referrals_config()
    record_config_access(user_id, is_bonus=is_bonus)''',
 '''    is_bonus = referrals >= get_required_referrals_config()
    record_config_access(user_id, is_bonus=is_bonus)
    if is_bonus:
        reset_user_progress(user_id)
        await callback.answer("🎉 چرخه دعوت از نو شروع شد!", show_alert=True)'''),
('''    if referral_count >= required_referrals:
        record_proxy_access(user_id, bonus=True)''',
 '''    if referral_count >= required_referrals:
        record_proxy_access(user_id, bonus=True)
        reset_user_progress(user_id)
        await callback.answer("🎉 چرخه دعوت از نو شروع شد!", show_alert=True)'''),
]
for i,(o,n) in enumerate(REPS,1):
    c=s.count(o)
    if c!=1:
        print(f"ANCHOR {i} FAIL count={c} (if already applied, ignore); backup={BAK}"); sys.exit(1)
    s=s.replace(o,n,1)
open(SRC,"w",encoding="utf-8").write(s)
try: py_compile.compile(SRC,doraise=True)
except py_compile.PyCompileError: print("COMPILE FAIL -> restore"); shutil.copy(BAK,SRC); sys.exit(1)
print("PATCH9_OK",len(REPS))
