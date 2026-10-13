import json, os, sys, time, asyncio, random, hashlib, re, urllib.request
import xml.etree.ElementTree as ET
import websockets
from post10 import nsec_to_hex, mul, G, sign, send, RELAYS, DIR

ADDR = "olivinepug15@primal.net"
LN_ADDRS = ["olivinepug15@primal.net", "predathorhaley@breez.tips", "chieftrait089@walletofsatoshi.com"]
FEEDS = [("https://www.criptonoticias.com/feed/", "CriptoNoticias"),
         ("https://es.cointelegraph.com/rss", "Cointelegraph en Espanol")]
BAD = ["airdrop", "giveaway", "casino", "apuestas"]
DRY = "--dry" in sys.argv

VALOR = [
"Security tip: never type your seed phrase into a website or send it to anyone, even 'support'. Real wallets never ask for it. 🔒 #Bitcoin #Security",
"Consejo: guarda tu frase semilla en papel o en metal, nunca en fotos ni en notas del teléfono. Quien la tenga controla tus fondos. 🔑 #Bitcoin #Seguridad",
"Lightning in one line: payments move between channels off-chain, so they are fast and cheap, and only opening or closing a channel touches the blockchain. ⚡ #Lightning #Bitcoin",
"Lightning para principiantes: una dirección tipo nombre@servidor funciona como un correo para recibir sats, sin copiar facturas largas. ⚡ #Lightning #Bitcoin",
"Not your keys, not your coins. Leaving funds on an exchange means trusting someone else with them. Self-custody has responsibilities, but you decide. 🔑 #Bitcoin #SelfCustody",
"Antes de enviar a una dirección nueva, haz una prueba pequeña. Una transacción de Bitcoin no se puede deshacer. ✅ #Bitcoin #Consejos",
"Phishing check: fake wallet apps and links copy the real ones. Install only from official sources and read the web address twice. 🛡️ #CyberSecurity #Crypto",
"Activa la verificación en dos pasos en tu correo y en tus cuentas, mejor con una app que por SMS. Los SIM swaps existen. 🔒 #Seguridad #Cripto",
"Nostr tip: your npub is public, your nsec is secret. Never paste your nsec into sites or apps you don't trust. Consider a signer like Amber. 🔑 #Nostr #Privacy",
"Consejo Nostr: usa un firmador como Amber en Android para que tu clave privada no esté guardada en cada aplicación. 🔑 #Nostr #Privacidad",
"Volatility is normal in crypto. Only use money you can afford to lose and never borrow to buy. This is education, not financial advice. 📉 #Bitcoin #Crypto",
"Diversificar no es adivinar: si tienes ahorros, entiende qué compras y por qué. Esto es educación, no consejo financiero. 📚 #Cripto #Finanzas",
"Low-resource tech tip: a cheap Android phone with Termux can run scripts, back up files and teach you Linux basics. Start small. 💻 #Termux #Linux",
"Seguridad personal: varía tus rutinas, observa tu entorno y no compartas tu ubicación en tiempo real. Los hábitos te protegen. 🛡️ #Seguridad #ProteccionPersonal",
]
THANKS = [
"Thank you for the zap{a}! ⚡🙏 Gracias por apoyar.",
"¡Gracias por el zap{a}! ⚡ Seguimos adelante. Thanks for the support!",
"Zap received{a}, thank you! ⚡ Se agradece de corazón. 🙏",
]

def build(sk, kind, content, tags):
    pub = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    ts = int(time.time())
    if kind == 1:
        tags = tags + [["t", t.lower()] for t in re.findall(r"#(\w+)", content)]
    raw = json.dumps([0, pub, ts, kind, tags, content], separators=(',', ':'), ensure_ascii=False)
    eid = hashlib.sha256(raw.encode()).digest()
    return {"id": eid.hex(), "pubkey": pub, "created_at": ts, "kind": kind,
            "tags": tags, "content": content, "sig": sign(eid, sk)}

async def publish(ev):
    if DRY:
        print("[DRY]", ev["content"]); return True
    res = await asyncio.gather(*[send(r, ev) for r in RELAYS])
    return any(res)

async def query(url, flt, wait=12):
    evs = []
    try:
        async with websockets.connect(url, open_timeout=30) as ws:
            await ws.send(json.dumps(["REQ", "v", flt]))
            end = time.time() + wait
            while time.time() < end:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), end - time.time()))
                except asyncio.TimeoutError:
                    break
                if m[0] == "EVENT": evs.append(m[2])
                elif m[0] == "EOSE": break
            await ws.send(json.dumps(["CLOSE", "v"]))
    except Exception as e:
        print(url, "error:", e)
    return evs

async def fetch(flt):
    res = await asyncio.gather(*[query(r, flt) for r in RELAYS])
    out = {}
    for lst in res:
        for e in lst: out[e["id"]] = e
    return list(out.values())

def get_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read()

def load():
    p = os.path.join(DIR, "valor.json")
    return json.load(open(p)) if os.path.exists(p) else {"i": 0, "news": [], "thanked": []}

def save(st):
    json.dump(st, open(os.path.join(DIR, "valor.json"), "w"))

async def do_nota(sk, st):
    i = st.get("i", 0)
    text = VALOR[i % len(VALOR)]
    if i % 3 == 2:
        text += "\n\n⚡ Zaps: " + ADDR
    if await publish(build(sk, 1, text, [])):
        st["i"] = i + 1
        print("Nota de valor publicada")

def read_feed(url):
    root = ET.fromstring(get_url(url))
    out = []
    for it in root.iter("item"):
        out.append(((it.findtext("title") or "").strip(),
                    (it.findtext("link") or "").strip(),
                    [(c.text or "") for c in it.findall("category")]))
    return out

async def do_news(sk, st):
    posted = st.setdefault("news", [])
    for url, name in FEEDS:
        try:
            items = read_feed(url)
        except Exception as e:
            print(url, "error:", e); continue
        for title, link, cats in items[:25]:
            if not title or not link or link in posted: continue
            if any("registrados" in c.lower() for c in cats): continue
            if any(b in title.lower() for b in BAD): continue
            text = ("📰 " + title + "\n\n" + link + "\n\nFuente: " + name +
                    ". Informativo, no es consejo financiero.\n#Bitcoin #Criptomonedas #Noticias")
            if await publish(build(sk, 1, text, [])):
                posted.append(link); st["news"] = posted[-200:]
                print("Noticia publicada:", title)
            return
    print("Sin noticias nuevas")

def providers():
    pks = set()
    for a in LN_ADDRS:
        try:
            u, d = a.split("@")
            j = json.loads(get_url("https://" + d + "/.well-known/lnurlp/" + u))
            if j.get("nostrPubkey"): pks.add(j["nostrPubkey"].lower())
        except Exception as e:
            print(a, "sin datos:", e)
    return pks

def sats(bolt):
    m = re.match(r"ln(?:bc|tb|bcrt)(\d+)([munp]?)", bolt.lower())
    if not m: return None
    mult = {"": 1, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12}[m.group(2)]
    return int(round(int(m.group(1)) * mult * 1e8))

async def do_zaps(sk, me, st):
    prov = providers()
    if not prov:
        print("No pude verificar los servidores de zaps. No hago nada."); return
    done = st.setdefault("thanked", [])
    recs = await fetch({"kinds": [9735], "#p": [me], "since": int(time.time()) - 3 * 86400, "limit": 50})
    n = 0
    for r in sorted(recs, key=lambda e: e["created_at"]):
        if n >= 10: break
        if r["id"] in done or r["pubkey"].lower() not in prov: continue
        desc = bolt = eid = None
        for t in r["tags"]:
            if len(t) > 1:
                if t[0] == "description": desc = t[1]
                elif t[0] == "bolt11": bolt = t[1]
                elif t[0] == "e" and eid is None: eid = t[1]
        try:
            sender = json.loads(desc).get("pubkey")
        except Exception:
            sender = None
        if not sender or sender == me or not eid:
            done.append(r["id"]); continue
        a = sats(bolt) if bolt else None
        text = random.choice(THANKS).format(a=(" (" + str(a) + " sats)") if a else "")
        if await publish(build(sk, 1, text, [["e", eid, "", "reply"], ["p", sender]])):
            done.append(r["id"]); n += 1
            await asyncio.sleep(random.randint(15, 30))
    st["thanked"] = done[-500:]
    print("Agradecimientos enviados:", n)

async def main():
    sk = nsec_to_hex(open(os.path.join(DIR, "nsec.txt")).read().strip())
    me = mul(G, int(sk, 16))[0].to_bytes(32, 'big').hex()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    st = load()
    print(time.strftime("%Y-%m-%d %H:%M"), mode, "(prueba)" if DRY else "")
    if mode == "nota": await do_nota(sk, st)
    elif mode == "noticias": await do_news(sk, st)
    elif mode == "zaps": await do_zaps(sk, me, st)
    else:
        print("Uso: python valor.py nota | noticias | zaps  (agrega --dry para probar sin publicar)"); return
    if not DRY: save(st)

asyncio.run(main())
