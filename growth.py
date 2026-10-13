import json, os, time, asyncio, random, hashlib
import websockets
from post10 import nsec_to_hex, mul, G, sign, send, RELAYS, DIR

TAGS=["grownostr","introductions","termux","cybersecurity","infosec","muaythai","mma","selfdefense","linux"]
MAX_FOLLOW=8
BAD=["airdrop","giveaway","pump","guaranteed","dm me","whatsapp","telegram","casino","f4f","follow4follow","onlyfans"]

def build(sk,kind,content,tags):
    pub=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    ts=int(time.time())
    raw=json.dumps([0,pub,ts,kind,tags,content],separators=(',',':'),ensure_ascii=False)
    eid=hashlib.sha256(raw.encode()).digest()
    return {"id":eid.hex(),"pubkey":pub,"created_at":ts,"kind":kind,
            "tags":tags,"content":content,"sig":sign(eid,sk)}

async def query(url,flt,wait=12):
    evs=[]
    try:
        async with websockets.connect(url,open_timeout=30) as ws:
            await ws.send(json.dumps(["REQ","g",flt]))
            end=time.time()+wait
            while time.time()<end:
                try:
                    m=json.loads(await asyncio.wait_for(ws.recv(),end-time.time()))
                except asyncio.TimeoutError:
                    break
                if m[0]=="EVENT": evs.append(m[2])
                elif m[0]=="EOSE": break
            await ws.send(json.dumps(["CLOSE","g"]))
    except Exception as e:
        print(url,"error:",e)
    return evs

async def fetch(flt):
    res=await asyncio.gather(*[query(r,flt) for r in RELAYS])
    out={}
    for lst in res:
        for e in lst: out[e["id"]]=e
    return list(out.values())

async def publish(ev):
    res=await asyncio.gather(*[send(r,ev) for r in RELAYS])
    return any(res)

def has_tag(e,name):
    return any(len(t)>1 and t[0]=="t" and t[1].lower()==name for t in e.get("tags",[]))

async def main():
    sk=nsec_to_hex(open(os.path.join(DIR,"nsec.txt")).read().strip())
    me=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    sf=os.path.join(DIR,"growth.json")
    st=json.load(open(sf)) if os.path.exists(sf) else {}
    st.setdefault("followed",[])
    today=time.strftime("%Y-%m-%d")
    if st.get("day")!=today:
        st["day"]=today; st["n"]=0
    now=int(time.time())
    print(time.strftime("%Y-%m-%d %H:%M"),"growth")

    fl=await fetch({"kinds":[3],"#p":[me],"limit":500})
    cnt=len({e["pubkey"] for e in fl})
    stf=os.path.join(DIR,"growth_stats.json")
    stats=json.load(open(stf)) if os.path.exists(stf) else []
    stats.append({"t":time.strftime("%Y-%m-%d %H:%M"),"seguidores_min":cnt})
    json.dump(stats[-200:],open(stf,"w"))
    print("Seguidores (minimo visible):",cnt)

    if st["n"]>=MAX_FOLLOW:
        print("Tope diario alcanzado"); json.dump(st,open(sf,"w")); return

    cl=await fetch({"kinds":[3],"authors":[me],"limit":5})
    if not cl:
        print("No pude leer tu lista de seguidos. No cambio nada por seguridad.")
        json.dump(st,open(sf,"w")); return
    cur=max(cl,key=lambda e:e["created_at"])
    json.dump(cur,open(os.path.join(DIR,"contactos_backup.json"),"w"))
    following={t[1] for t in cur["tags"] if t[0]=="p" and len(t)>1}

    posts=await fetch({"kinds":[1],"#t":TAGS,"since":now-86400,"limit":200})
    by={}
    for e in posts: by.setdefault(e["pubkey"],[]).append(e)

    cands=[]
    for pk,evs in by.items():
        if pk==me or pk in following or pk in st["followed"]: continue
        if len(evs)>12: continue
        if any(b in e["content"].lower() for e in evs for b in BAD): continue
        good=[e for e in evs if 40<=len(e["content"])<=800
              and e["content"].count("#")<=6 and e["content"].count("http")<=2]
        if not good: continue
        score=(2 if any(has_tag(e,"introductions") for e in evs) else 0)
        score+=(1 if len(evs)>=2 else 0)+random.random()
        cands.append((score,pk))
    cands.sort(reverse=True)
    pick=[pk for _,pk in cands[:MAX_FOLLOW-st["n"]]]
    if not pick:
        print("Sin candidatos nuevos esta vez"); json.dump(st,open(sf,"w")); return

    tags=list(cur["tags"])+[["p",pk] for pk in pick]
    ev=build(sk,3,cur.get("content",""),tags)
    if await publish(ev):
        st["followed"]+=pick; st["n"]+=len(pick)
        print("Nuevos seguidos:",len(pick))
    else:
        print("No se publico la lista")
    st["followed"]=st["followed"][-1000:]
    json.dump(st,open(sf,"w"))

asyncio.run(main())
