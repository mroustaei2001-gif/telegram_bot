import asyncio, os, json
from aiogram import Bot
with open("settings.json", encoding="utf-8") as f:
    S = json.load(f)
CH_ID = S.get("channel_id", "")
CH_LINK = S.get("channel_link", "")
ADMIN = int(os.getenv("ADMIN_ID", "6282695098"))
username = None
if CH_LINK:
    part = CH_LINK.rstrip("/").split("/")[-1]
    if part and not part.startswith("-"):
        username = "@" + part
async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    me = await bot.get_me()
    print("BOT id=", me.id, "user=", me.username)
    print("settings channel_id=", CH_ID, "username=", username)
    for label, target in [("ID", CH_ID), ("USER", username)]:
        if not target:
            print("get_chat", label, "skip"); continue
        try:
            c = await bot.get_chat(target)
            print(f"get_chat({label}) OK type={c.type} title={c.title} real_id={c.id}")
        except Exception as e:
            print(f"get_chat({label}) ERR {type(e).__name__} {str(e)[:120]}")
    for label, target in [("ID", CH_ID), ("USER", username)]:
        if not target: continue
        try:
            m = await bot.get_chat_member(target, ADMIN)
            print(f"member(ADMIN,{label}) = {m.status}")
        except Exception as e:
            print(f"member(ADMIN,{label}) ERR {type(e).__name__} {str(e)[:120]}")
    for label, target in [("ID", CH_ID), ("USER", username)]:
        if not target: continue
        try:
            m = await bot.get_chat_member(target, me.id)
            print(f"member(BOT,{label}) = {m.status}")
        except Exception as e:
            print(f"member(BOT,{label}) ERR {type(e).__name__} {str(e)[:120]}")
asyncio.run(main())
