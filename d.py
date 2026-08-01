import requests,os,json
T=os.getenv("BOT_TOKEN")
S=json.load(open("settings.json"))
u="https://api.telegram.org/bot"+T+"/getChat"
r=requests.post(u,json={"chat_id":S["channel_id"]})
print(r.json())
