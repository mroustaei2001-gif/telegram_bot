#!/usr/bin/env python3
import os,sys,secrets,string,subprocess,time
N=30; IP,PORT="91.107.157.255",1080
BASE="/var/socks5"; CFG=BASE+"/c.cfg"
os.makedirs(BASE,exist_ok=True)
try: os.chmod(BASE,0o777)
except Exception: pass
os.system("apt-get install -y curl >/dev/null 2>&1")
URL="http://ipv4.download.thinkbroadband.com/5MB.zip"
def rnd(n=10): return ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(n))
def run(c): return subprocess.run(c,capture_output=True,text=True)
def dl(u,p,mt=25):
    r=run(["curl","-s","-o","/dev/null","-w","%{size_download}","--max-time",str(mt),"-x","socks5://%s:%s@127.0.0.1:%d"%(u,p,PORT),URL])
    try: return float(r.stdout.strip())
    except Exception: return -1.0
def killall():
    os.system("systemctl stop socks5proxy 2>/dev/null; systemctl disable socks5proxy 2>/dev/null; pkill -9 3proxy 2>/dev/null")
    for _ in range(8):
        if ":1080" not in run(["ss","-tlnp"]).stdout: return True
        time.sleep(0.5)
    return ":1080" not in run(["ss","-tlnp"]).stdout
def daemon():
    return subprocess.Popen(["/usr/local/bin/3proxy",CFG],stdout=open(BASE+"/run.log","ab"),stderr=subprocess.STDOUT,start_new_session=True)
def trycfg(label,cfg,tu,tp):
    if not killall(): print(label,"PORT_BUSY"); return -1.0
    open(BASE+"/run.log","wb").close()
    open(CFG,"w").write(cfg)
    daemon(); time.sleep(3)
    listen=":1080" in run(["ss","-tlnp"]).stdout
    s=dl(tu,tp) if listen else -1.0
    print(label,"listen=%s size=%.0f"%(listen,s)); return s
real=[(i,"u%d"%i,rnd()) for i in range(1,N+1)]
pw1=rnd()
cfg1="log %s/log D\nauth strong\nusers t1:CL:%s\nallow *\nsocks -p%d\n"%(BASE,pw1,PORT)
cfg2="log %s/log D\nauth strong\n%s\nallow *\nsocks -p%d\n"%(BASE,"\n".join("users %s:CL:%s"%(u,p) for _,u,p in real),PORT)
cfg3="log %s/log D\nauth strong\nusers %s\nallow *\nsocks -p%d\n"%(BASE,",".join("%s:CL:%s"%(u,p) for _,u,p in real),PORT)
s1=trycfg("T1_1user",cfg1,"t1",pw1)
if s1<100000:
    print("ENV_BROKEN:"); os.system("cat %s/run.log %s/log* 2>/dev/null"%(BASE,BASE)); sys.exit(2)
ok=None
s2=trycfg("T2_30_multi",cfg2,real[0][1],real[0][2])
if s2>100000: ok="multi"
else:
    s3=trycfg("T3_30_comma",cfg3,real[0][1],real[0][2])
    if s3>100000: ok="comma"
if not ok:
    print("MULTIUSER_FAIL:"); os.system("tail -30 %s/log* 2>/dev/null; echo RUNLOG; cat %s/run.log 2>/dev/null"%(BASE,BASE)); sys.exit(3)
os.system("ufw allow 1080/tcp 2>/dev/null")
os.system("(crontab -l 2>/dev/null | grep -v '3proxy /var/socks5'; echo '@reboot sleep 8 && /usr/local/bin/3proxy %s') | crontab -"%CFG)
links=["https://t.me/socks?server=%s&port=%d&user=%s&pass=%s"%(IP,PORT,u,p) for _,u,p in real]
open(BASE+"/socks_links.txt","w").write("\n".join(links)+"\n")
open(BASE+"/creds.txt","w").write("\n".join("%s\t%s"%(u,p) for _,u,p in real)+"\n")
print("DONE 30 mode=UNLIMITED via",ok)
