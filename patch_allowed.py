import sys, shutil, py_compile
FILE = "bot py.py"
src = open(FILE, encoding="utf-8").read()
shutil.copy(FILE, FILE + ".preallowed.bak")
if "allowed_updates" in src:
    print("ALREADY_HAS_ALLOWED")
elif "await dp.start_polling(bot)" in src:
    src = src.replace("await dp.start_polling(bot)", 'await dp.start_polling(bot, allowed_updates=["message","callback_query","channel_post","chat_member"])', 1)
    open(FILE, "w", encoding="utf-8").write(src)
    try:
        py_compile.compile(FILE, doraise=True); print("ALLOWED_OK")
    except Exception as e:
        print("ERR", e); shutil.copy(FILE + ".preallowed.bak", FILE); sys.exit(1)
else:
    print("ERR_NO_ANCHOR")
