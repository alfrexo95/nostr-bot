import json, os, sys, time, asyncio, random, hashlib, re, secrets
import websockets

ADDR = "olivinepug15@primal.net"
MAX_FOLLOW = 4
TAGS_TO_FOLLOW = ["grownostr", "introductions", "termux", "cybersecurity", "muaythai"]
RELAYS = ["wss://relay.primal.net", "wss://relay.damus.io", "wss://nos.lol", "wss://relay.snort.social"]

THANKS_REPLIES = [
    "Thanks for the reply! 🙏 Glad you're here.",
    "Appreciate you stopping by. Let's grow together! ⚡",
    "Thank you! What's your take on this? Let me know 👇",
    "Good point, thanks for sharing your view. 💪",
    "Welcome! Glad to have you in the community. 🤝",
    "¡Gracias por el apoyo! / Thanks for the support! ⚡",
    "Muchas gracias por comentar, se agradece de corazón. 🇨🇺",
    "That's a great perspective. Have you tried it yourself?",
    "Thanks! If you like this kind of content, feel free to zap or repost. ⚡"
]

HISTORY_POSTS = [
    "Hi Nostr 👋 I'm Alfred from Cuba 🇨🇺. Ex-special forces, close protection, MMA and Muay Thai, and I build tools with Termux. I post about security, discipline and tech with low resources. #introductions #grownostr",
    "Close protection lesson #1: the best bodyguard is awareness. Know your exits, watch the hands, trust your instincts. 🛡️ #Security #CloseProtection #grownostr",
    "Cuba taught me that you don't need much to start. A phone, a connection and stubborn curiosity are enough to learn almost anything. What's the one tool you started with? 📱 #Mindset #Cuba",
    "Your private key is your identity on Nostr. No company owns your followers, no algorithm owns your voice. Back it up, protect it, never share it. 🔑 #Nostr #Privacy",
    "Training MMA and Muay Thai taught me that comfort is a trap. Every session you want to quit is a session that builds you. Do you train? 🥊 #MMA #Discipline",
    "Turn your old Android phone into a tiny server. With Termux you can run scripts, bots and tools for free. 💻 #Termux #Linux #Android"
]

p = 2**256 - 2**32 - 977
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def add(P, Q):
    if P is None: return Q
    if Q is None: return P
    if P[0] == Q[0] and (P[1] + Q[1]) % p == 0: return None
    l = 3 * P[0] * P[0] * pow(2 * P[1], -1, p) % p if P == Q else (Q[1] - P[1]) * pow(Q[0] - P[0], -1, p) % p
    x = (l * l - P[0] - Q[0]) % p
    return (x, (l * (P[0] - x) - P[1]) % p)

def mul(P, k):
    R = None
    while k:
        if k & 1: R = add(R, P)
        P = add(P, P); k >>= 1
    return R

def th(tag, *b):
    t = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(t + t + b"".join(b)).digest()

def nsec_to_hex(s):
    C = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    acc = bits = 0; out = []
    for c in s[5:-6]:
        acc = (acc << 5) | C.index(c); bits += 5
        while bits >= 8:
            bits -= 8; out.append((acc >> bits) & 255)
        acc &= (1 << bits) - 1
    return bytes(out).hex()

def sign(msg, sk):
    d = int(sk, 16); P = mul(G, d)
    if P[1] % 2: d = n - d
    px = P[0].to_bytes(32, 'big')
    t = (d ^ int.from_bytes(th("BIP0340/aux", secrets.token_bytes(32)), 'big')).to_bytes(32, 'big')
    k = int.from_bytes(th("BIP0340/nonce", t, px, msg), 'big') % n
    R = mul(G, k)
    if R[1] % 2: k = n - k
    rx = R[0].to_bytes(32, 'big')
    e = int.from_bytes(th("BIP0340/challenge", rx, px, msg), 'big') % n
    return (rx + ((k + e * d) % n).to_bytes(32, 'big')).hex()

def build(sk, kind, content, tags=None):
    if tags is None: tags = []
    if kind == 1: tags += [["t", t.lower()] for t in re.findall(r"#(\w+)", content)]
    pub = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    ts = int(time.time())
    raw = json.dumps([0, pub, ts, kind, tags, content], separators=(',', ':'), ensure_ascii=False)
    eid = hashlib.sha256(raw.encode()).digest()
    return {"id": eid.hex(), "pubkey": pub, "created_at": ts, "kind": kind, "tags": tags, "content": content, "sig": sign(eid, sk)}

async def send(url, ev):
    try:
        async with websockets.connect(url, open_timeout=15) as ws:
            await ws.send(json.dumps(["EVENT", ev]))
            r = json.loads(await asyncio.wait_for(ws.recv(), 15))
            return bool(r[0] == "OK" and r[2])
    except Exception:
        return False

async def query(url, flt):
    evs = []
    try:
        async with websockets.connect(url, open_timeout=15) as ws:
            await ws.send(json.dumps(["REQ", "q", flt]))
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), 8))
                except asyncio.TimeoutError:
                    break
                if m[0] == "EVENT": evs.append(m[2])
                elif m[0] == "EOSE": break
    except Exception:
        pass
    return evs

def load_state():
    if os.path.exists("state.json"):
        return json.load(open("state.json"))
    return {"replied": [], "followed": [], "post_idx": 0, "thanked": []}

def save_state(st):
    json.dump(st, open("state.json", "w"))

async def main():
    nsec = os.environ.get("NOSTR_NSEC", "").strip()
    if not nsec:
        print("❌ Falta NOSTR_NSEC")
        return
    sk = nsec_to_hex(nsec)
    me = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    st = load_state()
    
    # 1. Publicar historia
    post_text = HISTORY_POSTS[st["post_idx"] % len(HISTORY_POSTS)]
    if await send(RELAYS[0], build(sk, 1, post_text)):
        st["post_idx"] += 1
        print("📝 Historia publicada")

    # 2. Agradecer zaps
    zaps = await query(RELAYS[0], {"kinds": [9735], "#p": [me], "limit": 10})
    for z in zaps:
        if z["id"] in st["thanked"]: continue
        sender = next((t[1] for t in z["tags"] if t[0] == "p"), None)
        if sender and sender != me:
            reply = random.choice(THANKS_REPLIES)
            if await send(RELAYS[0], build(sk, 1, reply, [["e", z["id"], "", "reply"], ["p", sender]])):
                st["thanked"].append(z["id"])
                print("⚡ Zap agradecido")
                await asyncio.sleep(random.randint(5, 15))

    # 3. Responder menciones
    mentions = await query(RELAYS[0], {"kinds": [1], "#p": [me], "limit": 15})
    for m in mentions:
        if m["id"] in st["replied"] or m["pubkey"] == me: continue
        reply = random.choice(THANKS_REPLIES)
        if await send(RELAYS[0], build(sk, 1, reply, [["e", m["id"], "", "reply"], ["p", m["pubkey"]]])):
            st["replied"].append(m["id"])
            print("💬 Respondido")
            await asyncio.sleep(random.randint(10, 30))

    # 4. Seguir a max 4 personas
    follows_count = 0
    cands = await query(RELAYS[0], {"kinds": [1], "#t": TAGS_TO_FOLLOW, "limit": 50})
    
    follow_list_ev = await query(RELAYS[0], {"kinds": [3], "authors": [me], "limit": 1})
    following = set()
    if follow_list_ev:
        following = set(t[1] for t in follow_list_ev[0]["tags"] if t[0] == "p")
    
    for c in cands:
        if follows_count >= MAX_FOLLOW: break
        if c["pubkey"] not in following and c["pubkey"] not in st["followed"]:
            if await send(RELAYS[0], build(sk, 3, "", [["p", c["pubkey"]]])):
                st["followed"].append(c["pubkey"])
                follows_count += 1
                print("👥 Seguido")
                await asyncio.sleep(5)

    save_state(st)
    print("✅ Ciclo terminado")

asyncio.run(main())
