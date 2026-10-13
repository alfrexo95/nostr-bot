import hashlib, json, time, os, asyncio, secrets, re
import websockets

p=2**256-2**32-977
n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
   0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
RELAYS=["wss://relay.damus.io","wss://nos.lol","wss://relay.primal.net","wss://relay.snort.social","wss://offchain.pub"]
DIR=os.path.dirname(os.path.abspath(__file__))

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
            print(url,await asyncio.wait_for(ws.recv(),20))
    except Exception as e:
        print(url,"error:",e)

async def main():
    sk=nsec_to_hex(open(os.path.join(DIR,"nsec.txt")).read().strip())
    posts=json.load(open(os.path.join(DIR,"posts.json"),encoding="utf-8"))
    sf=os.path.join(DIR,"state.txt")
    i=int(open(sf).read()) if os.path.exists(sf) else 0
    ev=make_event(sk,posts[i%len(posts)])
    print(time.strftime("%Y-%m-%d %H:%M"),"publicando #",i%len(posts)+1)
    await asyncio.gather(*[send(r,ev) for r in RELAYS])
    open(sf,"w").write(str(i+1))

asyncio.run(main())
