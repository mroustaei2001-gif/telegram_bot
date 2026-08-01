import shutil, py_compile, sys
SRC = "bot py.py"
BAK = SRC + ".prepatch11.bak"
shutil.copy(SRC, BAK)
s = open(SRC, encoding="utf-8").read()
REPS = [
('''def add_proxy(proxy_string):
    proxies = load_proxies()
    proxies.append(proxy_string)
    save_proxies(proxies)''',
 '''def store_proxy(proxy_string):
    proxies = load_proxies()
    proxies.append(proxy_string)
    save_proxies(proxies)'''),
('''    proxy_string = message.text.strip()
    add_proxy(proxy_string)''',
 '''    proxy_string = message.text.strip()
    store_proxy(proxy_string)'''),
]
for i,(o,n) in enumerate(REPS,1):
    c=s.count(o)
    if c!=1:
        print(f"ANCHOR {i} FAIL count={c}; backup={BAK}"); sys.exit(1)
    s=s.replace(o,n,1)
open(SRC,"w",encoding="utf-8").write(s)
try: py_compile.compile(SRC,doraise=True)
except py_compile.PyCompileError: print("COMPILE FAIL -> restore"); shutil.copy(BAK,SRC); sys.exit(1)
print("PATCH11_OK",len(REPS))
