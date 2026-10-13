import hashlib, json, time, os, asyncio, secrets, re
import websockets

POSTS = [
"Hi Nostr 👋 I'm Alfred from Cuba 🇨🇺. Ex-special forces, close protection, MMA and Muay Thai, and I build tools with Termux. I post about security, discipline and tech with low resources. Follow me if that's your thing, and tell me where you're from! #introductions #grownostr #Nostr",
"Close protection lesson #1: the best bodyguard is awareness. Know your exits, watch the hands, trust your instincts. Want more security tips like this? Follow me, I share them here regularly. 🛡️ #Security #CloseProtection #grownostr",
"Cuba taught me that you don't need much to start. A phone, a connection and stubborn curiosity are enough to learn almost anything. What's the one tool you started with? Tell me below 👇 and follow for more. 📱 #Mindset #Cuba #grownostr",
"Your private key is your identity on Nostr. No company owns your followers, no algorithm owns your voice. Back it up, protect it, never share it. New here? Follow me and I'll share beginner tips. 🔑 #Nostr #Privacy #grownostr",
"Training MMA and Muay Thai taught me that comfort is a trap. Every session you want to quit is a session that builds you. Do you train? Drop your sport below and follow if you like discipline content. 🥊 #MMA #MuayThai #Discipline",
"Turn your old Android phone into a tiny server. With Termux you can run scripts, bots and tools for free. Want a step-by-step guide? Follow me and I'll share it. 💻 #Termux #Linux #Android #grownostr",
"Security habit that costs nothing: turn on two-factor authentication on every important account today. Repost this for someone who still reuses passwords, and follow for more quick security habits. 🔒 #CyberSecurity #2FA #grownostr",
"Discipline is a promise you keep to yourself when nobody is watching. Small actions, repeated daily, beat big plans you never start. What's your daily habit? Share it below and follow along. 💪 #Discipline #Habits #grownostr",
"Zaps changed how I think about the internet. Value flows directly from person to person, in seconds, with no middleman. Who is the best creator you follow on Nostr? Tag them below so we can all follow them. ⚡ #Zaps #Nostr #Bitcoin #grownostr",
"Thank you for being here. I share what I learn from Cuba about security, tech and resilience. If it helps you, follow, repost it for someone who needs it, or send a zap to keep it going. 🙏 #Nostr #Bitcoin #Community #grownostr",
]
MAX_PER_MONTH = 10
INTERVAL_DAYS = 3
RELAYS=["wss://relay.primal.net","wss://relay.damus.io","wss://nos.lol","wss://relay.snort.social","wss://offchain.pub"]
DIR=os.path.dirname(os.path.abspath(__file__))

p=2**256-2**32-977
n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
   0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def add(P,Q):
    if P is None: return Q
    if Q is None: return P
    if P[0]==Q[0] and (P[1]+Q[1])%p==0: return None
    l=3*P[0]*P[0]*pow(2*P[1],-1,p)%p if P==Q else (Q[1]-P[1])*pow(Q[0]-P[0],-1,p)%p
    x=(l*l-P[0]-Q[0])%p
    return (x,(l*(P[0]-x)-P[1])%p)

def mul(P,k):
    R=None
    while k:
        if k&1: R=add(R,P)
        P=add(P,P); k>>=1
    return R

def th(tag,*b):
    t=hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(t+t+b"".join(b)).digest()

def nsec_to_hex(s):
    C="qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    acc=bits=0; out=[]
    for c in s[5:-6]:
        acc=(acc<<5)|C.index(c); bits+=5
        while bits>=8:
            bits-=8; out.append((acc>>bits)&255)
        acc&=(1<<bits)-1
    return bytes(out).hex()

def sign(msg,sk):
    d=int(sk,16); P=mul(G,d)
    if P[1]%2: d=n-d
    px=P[0].to_bytes(32,'big')
    t=(d^int.from_bytes(th("BIP0340/aux",secrets.token_bytes(32)),'big')).to_bytes(32,'big')
    k=int.from_bytes(th("BIP0340/nonce",t,px,msg),'big')%n
    R=mul(G,k)
    if R[1]%2: k=n-k
    rx=R[0].to_bytes(32,'big')
    e=int.from_bytes(th("BIP0340/challenge",rx,px,msg),'big')%n
    return (rx+((k+e*d)%n).to_bytes(32,'big')).hex()

def make_event(sk,content,kind=1):
    tags=[["t",t.lower()] for t in re.findall(r"#(\w+)",content)]
    pub=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    ts=int(time.time())
    raw=json.dumps([0,pub,ts,kind,tags,content],separators=(',',':'),ensure_ascii=False)
    eid=hashlib.sha256(raw.encode()).digest()
    return {"id":eid.hex(),"pubkey":pub,"created_at":ts,"kind":kind,
            "tags":tags,"content":content,"sig":sign(eid,sk)}

async def send(url,ev):
    try:
        async with websockets.connect(url,open_timeout=30) as ws:
            await ws.send(json.dumps(["EVENT",ev]))
            r=json.loads(await asyncio.wait_for(ws.recv(),20))
            print(url,r)
            return bool(r[0]=="OK" and r[2])
    except Exception as e:
        print(url,"error:",e)
        return False

async def main():
    sf=os.path.join(DIR,"state10.json")
    st=json.load(open(sf)) if os.path.exists(sf) else {"index":0,"last":0,"month":"","count":0}
    now=time.time()
    month=time.strftime("%Y-%m")
    if st["month"]!=month:
        st["month"]=month; st["count"]=0
    print(time.strftime("%Y-%m-%d %H:%M"))
    if now-st["last"] < INTERVAL_DAYS*86400-3600:
        print("Aun no toca publicar"); return
    if st["count"]>=MAX_PER_MONTH:
        print("Limite mensual alcanzado"); return
    sk=nsec_to_hex(open(os.path.join(DIR,"nsec.txt")).read().strip())
    i=st["index"]%len(POSTS)
    print("Publicando #",i+1)
    ev=make_event(sk,POSTS[i])
    res=await asyncio.gather(*[send(r,ev) for r in RELAYS])
    if any(res):
        st["index"]+=1; st["last"]=now; st["count"]+=1
        json.dump(st,open(sf,"w"))
        print("Publicada en",sum(res),"relays")
    else:
        print("No se publico en ningun relay. Se reintenta manana.")

if __name__=="__main__": asyncio.run(main())
