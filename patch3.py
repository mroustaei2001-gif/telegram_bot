import sys, shutil, py_compile
FILE = "bot py.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()
shutil.copy(FILE, FILE + ".prepatch3.bak")
errs = []
def repl(old, new, label):
    global src
    if old not in src:
        errs.append(label); return
    src = src.replace(old, new, 1); print("  ok", label)

# R1: /start را در middleware استثنا کن (cmd_start خودش عضویت را چک می‌کند)
repl(
'        if isinstance(event, CallbackQuery) and event.data == "check_join":\n'
'            return await handler(event, data)\n',
'        if isinstance(event, CallbackQuery) and event.data == "check_join":\n'
'            return await handler(event, data)\n'
'        if isinstance(event, Message) and event.text and event.text.startswith("/start"):\n'
'            return await handler(event, data)\n',
"R1-start-exempt")

# R2: verify لیست خام را دست نزند، فقط معتبرها را بشمارد
repl(
'async def verify_referrals(user_id):\n'
'    refs = load_referrals()\n'
'    key = str(user_id)\n'
'    user_refs = refs.get(key, [])\n'
'    channel_id = get_channel_id()\n'
'    if not channel_id or not user_refs:\n'
'        return len(user_refs)\n'
'    valid = []\n'
'    for ref_id in user_refs:\n'
'        try:\n'
'            member = await bot.get_chat_member(channel_id, int(ref_id))\n'
'            if member.status in ("member", "administrator", "creator"):\n'
'                valid.append(ref_id)\n'
'        except Exception:\n'
'            valid.append(ref_id)\n'
'    refs[key] = valid\n'
'    save_referrals(refs)\n'
'    return len(valid)\n',
'async def verify_referrals(user_id):\n'
'    refs = load_referrals()\n'
'    key = str(user_id)\n'
'    user_refs = refs.get(key, [])\n'
'    channel_id = get_channel_id()\n'
'    if not channel_id or not user_refs:\n'
'        return len(user_refs)\n'
'    valid = 0\n'
'    for ref_id in user_refs:\n'
'        try:\n'
'            member = await bot.get_chat_member(channel_id, int(ref_id))\n'
'            if member.status in ("member", "administrator", "creator"):\n'
'                valid += 1\n'
'        except Exception:\n'
'            pass\n'
'    return valid\n',
"R2-verify-keep-raw")

# R3: can_user_get_config تعداد معتبر را بگیرد
repl(
'def can_user_get_config(user_id):\n'
'    data = load_config_access()\n'
'    key = str(user_id)\n'
'    if key not in data:\n'
'        return True, 0\n'
'    last = datetime.fromisoformat(data[key]["last_access"])\n'
'    hours = (datetime.now() - last).total_seconds() / 3600\n'
'    if hours >= 24:\n'
'        return True, 0\n'
'    if get_referral_count(user_id) >= get_required_referrals_config() and not data[key].get("bonus_used", False):\n'
'        return True, get_required_referrals_config()\n'
'    return False, int(24 - hours)\n',
'def can_user_get_config(user_id, referral_count=None):\n'
'    data = load_config_access()\n'
'    key = str(user_id)\n'
'    if key not in data:\n'
'        return True, 0\n'
'    last = datetime.fromisoformat(data[key]["last_access"])\n'
'    hours = (datetime.now() - last).total_seconds() / 3600\n'
'    if hours >= 24:\n'
'        return True, 0\n'
'    rc = referral_count if referral_count is not None else get_referral_count(user_id)\n'
'    if rc >= get_required_referrals_config() and not data[key].get("bonus_used", False):\n'
'        return True, get_required_referrals_config()\n'
'    return False, int(24 - hours)\n',
"R3-config-uses-valid")

# R4: confirm_config -> valid را پاس بده
repl(
'    await verify_referrals(user_id)\n'
'    can_access, info = can_user_get_config(user_id)\n',
'    valid = await verify_referrals(user_id)\n'
'    can_access, info = can_user_get_config(user_id, valid)\n',
"R4-confirm-config-valid")

# R5: confirm_config -> bonus بر اساس معتبر
repl(
'    referrals = get_referral_count(user_id)\n'
'    is_bonus = referrals >= get_required_referrals_config()\n',
'    referrals = valid\n'
'    is_bonus = referrals >= get_required_referrals_config()\n',
"R5-confirm-config-bonus")

# R6: confirm_proxy -> valid
repl(
'    await verify_referrals(user_id)\n'
'    can_access, last_access = can_user_access_proxy(user_id)\n',
'    valid = await verify_referrals(user_id)\n'
'    can_access, last_access = can_user_access_proxy(user_id)\n',
"R6-confirm-proxy-valid")

# R7: confirm_proxy -> bonus بر اساس معتبر
repl(
'    referral_count = get_referral_count(user_id)\n'
'    required_referrals = get_required_referrals()\n',
'    referral_count = valid\n'
'    required_referrals = get_required_referrals()\n',
"R7-confirm-proxy-bonus")

# R8: referral_menu -> valid بگیر
repl(
'    await verify_referrals(user_id)\n'
'    count = get_referral_count(user_id)\n',
'    valid = await verify_referrals(user_id)\n'
'    count = get_referral_count(user_id)\n',
"R8-menu-valid")

# R9: referral_menu -> متن خام + معتبر
repl(
'            f"✅ دعوت‌های معتبر: <b>{count}</b>\\n"\n'
'            f"🎁 پروکسی ویژه: {count}/{req_proxy}\\n"\n'
'            f"🔑 کانفیگ فوری: {count}/{req_config}\\n\\n"',
'            f"👥 وارد ربات شده: {count}\\n"\n'
'            f"✅ عضو کانال (معتبر): <b>{valid}</b>\\n"\n'
'            f"🎁 پروکسی ویژه: {valid}/{req_proxy}\\n"\n'
'            f"🔑 کانفیگ فوری: {valid}/{req_config}\\n\\n"',
"R9-menu-text")

if errs:
    print("\n❌ anchorهای پیدا نشده:"); [print("  -", e) for e in errs]
    print("⛔ فایل تغییر نکرد. backup:", FILE + ".prepatch3.bak"); sys.exit(1)
with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
try:
    py_compile.compile(FILE, doraise=True)
    print("\n✅ patch3 اعمال شد (9 تغییر) و syntax درست است.")
except py_compile.PyCompileError as e:
    print("\n❌ syntax:", e); shutil.copy(FILE + ".prepatch3.bak", FILE); sys.exit(1)
