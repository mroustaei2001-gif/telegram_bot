import sys, shutil, py_compile
FILE = "bot py.py"
with open(FILE, encoding="utf-8") as f:
    src = f.read()
shutil.copy(FILE, FILE + ".prepatch2.bak")
old = "    if is_force_join_enabled() and channel_id:\n"
new = "    if str(user_id) != ADMIN_ID and is_force_join_enabled() and channel_id:\n"
c = src.count(old)
if c == 0:
    print("ERR anchor not found"); sys.exit(1)
src = src.replace(old, new)
with open(FILE, "w", encoding="utf-8") as f:
    f.write(src)
try:
    py_compile.compile(FILE, doraise=True)
    print("OK patched internal checks:", c, "(admin exempted). syntax ok")
except py_compile.PyCompileError as e:
    print("ERR", e); shutil.copy(FILE + ".prepatch2.bak", FILE); sys.exit(1)
