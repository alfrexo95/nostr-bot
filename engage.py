import json, os, time, asyncio, random, hashlib
import websockets
from post10 import nsec_to_hex, mul, G, sign, send, RELAYS, DIR

TAGS=["grownostr","introductions","termux","cybersecurity","muaythai"]
MAX_REACT=5
MAX_REPLY=5
THANKS=[
"Thanks for the reply! 🙏",
"Appreciate you stopping by. Glad it resonated. ⚡",
"Thank you! Curious what you think, have you tried it yourself?",
"Good point, thanks for sharing your view. 💪",
"Welcome! Glad to have you here. 🤝",
]

def build(sk,kind,content,tags):
    pub=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    ts=int(time.time())
    raw=json.dumps([0,pub,ts,kind,tags,content],separators=(',',':'),ensure_ascii=False)
    eid=hashlib.sha256(raw.encode()).digest()
    return {"id":eid.hex(),"pubkey":pub,"created_at":ts,"kind":kind,
            "tags":tags,"content":content,"sig":sign(eid,sk)}

async def query(url,flt,wait=10):
    evs=[]
    try:
        async with websockets.connect(url,open_timeout=30) as ws:
            await ws.send(json.dumps(["REQ","q",flt]))
            end=time.time()+wait
            while time.time()<end:
                try:
                    m=json.loads(await asyncio.wait_for(ws.recv(),end-time.time()))
                except asyncio.TimeoutError:
                    break
                if m[0]=="EVENT": evs.append(m[2])
                elif m[0]=="EOSE": break
    except Exception as e:
        print(url,"error:",e)
    return evs

async def fetch(flt):
    res=await asyncio.gather(*[query(r,flt) for r in RELAYS[:3]])
    out={}
    for lst in res:
        for e in lst: out[e["id"]]=e
    return list(out.values())

async def publish(ev):
    res=await asyncio.gather(*[send(r,ev) for r in RELAYS])
    return any(res)

async def main():
    sk=nsec_to_hex(open(os.path.join(DIR,"nsec.txt")).read().strip())
    me=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    sf=os.path.join(DIR,"engage.json")
    st=json.load(open(sf)) if os.path.exists(sf) else {}
    st.setdefault("reacted",[]); st.setdefault("replied",[])
    today=time.strftime("%Y-%m-%d")
    if st.get("day")!=today:
        st["day"]=today; st["r"]=0; st["p"]=0
    now=int(time.time())
    print(time.strftime("%Y-%m-%d %H:%M"),"engage")

    if st["r"]<MAX_REACT:
        found=await fetch({"kinds":[1],"#t":TAGS,"since":now-6*3600,"limit":40})
        random.shuffle(found)
        for e in found:
            if st["r"]>=MAX_REACT: break
            if e["pubkey"]==me or e["id"] in st["reacted"]: continue
            if await publish(build(sk,7,"🔥",[["e",e["id"]],["p",e["pubkey"]]])):
                st["reacted"].append(e["id"]); st["r"]+=1
                await asyncio.sleep(random.randint(15,45))

    if st["p"]<MAX_REPLY:
        ments=await fetch({"kinds":[1],"#p":[me],"since":now-3*86400,"limit":30})
        for e in ments:
            if st["p"]>=MAX_REPLY: break
            if e["pubkey"]==me or e["id"] in st["replied"]: continue
            tags=[["e",e["id"],"","reply"],["p",e["pubkey"]]]
            if await publish(build(sk,1,random.choice(THANKS),tags)):
                st["replied"].append(e["id"]); st["p"]+=1
                await asyncio.sleep(random.randint(15,45))

    st["reacted"]=st["reacted"][-500:]; st["replied"]=st["replied"][-500:]
    json.dump(st,open(sf,"w"))
    print("Hoy: reacciones",st["r"],"respuestas",st["p"])

asyncio.run(main())
