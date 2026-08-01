import shutil, py_compile, sys
SRC = "bot py.py"
BAK = SRC + ".prepatch10.bak"
shutil.copy(SRC, BAK)
s = open(SRC, encoding="utf-8").read()

REPS = [
# R1: refresh button -> catch not-modified + give feedback
('''@dp.callback_query(F.data == "refresh_referral")
async def refresh_referral(callback: CallbackQuery):
    await referral_menu(callback)''',
 '''@dp.callback_query(F.data == "refresh_referral")
async def refresh_referral(callback: CallbackQuery):
    try:
        await referral_menu(callback)
        await callback.answer("🔄 به‌روز شد")
    except TelegramBadRequest:
        await callback.answer("🔄 چک شد (تعداد فعلاً تغییر نکرد)")'''),

# R2: diagnostic log at start of chat_member handler
('''async def on_ref_chat_member(update: ChatMemberUpdated):
    try:
        if str(update.chat.id) != get_channel_id():
            return''',
 '''async def on_ref_chat_member(update: ChatMemberUpdated):
    try:
        logging.info("CM_EVT chat=%s link=%s old=%s new=%s", update.chat.id, (update.invite_link.invite_link if update.invite_link else None), update.old_chat_member.status, update.new_chat_member.status)
        if str(update.chat.id) != get_channel_id():
            return'''),
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
print("PATCH10_OK applied", len(REPS), "changes")
