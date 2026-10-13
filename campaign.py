import json, os, sys, time, asyncio, hashlib, re
from urllib.parse import quote
from post10 import nsec_to_hex, mul, G, sign, send, RELAYS, DIR

ADDR = "olivinepug15@primal.net"
GEYSER = ""   # pega aqui el enlace de tu campana en Geyser (opcional)
TITLE = "Computer education for Cuba and Central America"

NOTES = [
"Most people in Cuba and Central America have a phone but no one to teach them how to use it to build a future. I want to change that: practical computer skills, taught with the few resources we have. Any amount of sats helps ⚡ {addr} #Bitcoin #Education #Nostr",
"Si alguien aprende informática, aprende a trabajar con el mundo entero. Quiero llevar esa oportunidad a personas en Cuba y Centroamérica que no tienen acceso. Con unos pocos sats ayudas a que sea posible ⚡ {addr} #Bitcoin #Educación #Nostr",
"Why sats and Lightning? Because they reach people who banks don't. No borders, no middlemen, no waiting. Your contribution arrives in seconds and goes straight to the project. ⚡ {addr} #Lightning #Bitcoin #grownostr",
"¿Qué se logra con tu aporte? Materiales de estudio, tiempo para enseñar y datos de internet para que más gente pueda aprender. Todo suma, aunque sea poco. ⚡ {addr} #Bitcoin #Lightning #Cuba",
"I won't promise miracles. I promise to teach, to show progress and to thank every person who helps. If you can't send sats, a repost helps just as much. 🙏 {addr} #Nostr #Bitcoin #Community",
"No puedes donar? Compartir esta nota también es ayudar. Cada repost la lleva a alguien que sí puede apoyar. Gracias por estar aquí. 🙏 {addr} #Nostr #Bitcoin #Comunidad",
"Update: the project keeps moving, one lesson at a time. Thank you to everyone who zapped or shared. If you want to join, my Lightning address is {addr} ⚡ #Bitcoin #Education #grownostr",
"Mil gracias a quienes ya apoyaron con zaps y reposts. El camino es largo, pero cada clase cuenta. Si quieres sumarte, mi dirección Lightning es {addr} ⚡ #Bitcoin #Educación #Nostr",
]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
body{font-family:sans-serif;max-width:520px;margin:auto;padding:20px;background:#111;color:#eee;line-height:1.5}
h1{font-size:24px;text-align:center}h2{font-size:18px;color:#f7931a;margin-top:28px}
.c{text-align:center}code{background:#222;padding:10px;border-radius:6px;display:block;margin:12px 0;word-break:break-all}
button{padding:10px 18px;border:0;border-radius:6px;background:#f7931a;font-size:16px}
a{color:#f7931a}details{background:#1b1b1b;padding:10px;border-radius:6px;margin:8px 0}
</style></head><body>
<h1>__TITLE__<br><small>Educación informática para Cuba y Centroamérica</small></h1>
<div class="c"><img src="__QR__" width="240" height="240" alt="QR"><code>__ADDR__</code>
<button onclick="navigator.clipboard.writeText('__ADDR__');this.textContent='Copied / Copiado'">Copy Lightning address</button>__GEYSER__</div>

<h2>The story / La historia</h2>
<p>I'm Alfred, from Cuba. I know how hard it is to learn technology with limited internet and almost no resources. I want to teach practical computer skills to people who rarely get the chance.</p>
<p>Soy Alfred, de Cuba. Sé lo difícil que es aprender tecnología con internet limitado y pocos recursos. Quiero enseñar informática práctica a personas que casi nunca tienen la oportunidad.</p>

<h2>Why it matters / Por qué importa</h2>
<ul>
<li>Computer skills open the door to remote work and income. / La informática abre la puerta al trabajo remoto y a ingresos propios.</li>
<li>Low-cost tools like a phone and Termux are enough to start. / Con un teléfono y herramientas gratuitas como Termux alcanza para empezar.</li>
<li>Knowledge multiplies: each person taught can teach others. / El conocimiento se multiplica: quien aprende puede enseñar a otros.</li>
</ul>

<h2>How funds are used / Cómo se usan los fondos</h2>
<ul>
<li>Learning materials and practice resources. / Materiales de estudio y práctica.</li>
<li>Internet data so students can follow lessons. / Datos de internet para seguir las clases.</li>
<li>Time dedicated to teaching and support. / Tiempo dedicado a enseñar y acompañar.</li>
</ul>

<h2>How to help / Cómo ayudar</h2>
<ul>
<li>Send any amount of sats via Lightning. / Envía sats por Lightning, la cantidad que quieras.</li>
<li>Share this page or the project notes. / Comparte esta página o las notas del proyecto.</li>
<li>Follow me on Nostr for progress updates. / Sígueme en Nostr para ver los avances.</li>
</ul>

<h2>FAQ</h2>
<details><summary>Do I need a Bitcoin wallet? / Necesito una billetera?</summary>Any Lightning wallet works: Wallet of Satoshi, Phoenix, Primal and more. / Sirve cualquier billetera Lightning.</details>
<details><summary>Is there a minimum? / Hay un mínimo?</summary>No. Even a few sats count. / No. Aunque sean pocos sats, cuentan.</details>
<details><summary>How will I know what happens? / Cómo sabré qué pasa?</summary>I'll post updates on Nostr. / Publicaré los avances en Nostr.</details>

<p class="c">Thank you / Gracias 🙏</p></body></html>"""

def build(sk,kind,content,tags):
    pub=mul(G,int(sk,16))[0].to_bytes(32,'big').hex()
    ts=int(time.time())
    if kind==1: tags=tags+[["t",t.lower()] for t in re.findall(r"#(\w+)",content)]
    raw=json.dumps([0,pub,ts,kind,tags,content],separators=(',',':'),ensure_ascii=False)
    eid=hashlib.sha256(raw.encode()).digest()
    return {"id":eid.hex(),"pubkey":pub,"created_at":ts,"kind":kind,
            "tags":tags,"content":content,"sig":sign(eid,sk)}

async def publish(ev):
    res=await asyncio.gather(*[send(r,ev) for r in RELAYS])
    return any(res)

def load():
    p=os.path.join(DIR,"campaign.json")
    return json.load(open(p)) if os.path.exists(p) else {"i":0}

def save(st):
    json.dump(st,open(os.path.join(DIR,"campaign.json"),"w"))

def page():
    qr="https://api.qrserver.com/v1/create-qr-code/?size=260x260&data="+quote(ADDR)
    g=f'<p><a href="{GEYSER}">Campaign on Geyser</a></p>' if GEYSER else ""
    html=(PAGE.replace("__TITLE__",TITLE).replace("__QR__",qr)
          .replace("__ADDR__",ADDR).replace("__GEYSER__",g))
    open(os.path.join(DIR,"campana.html"),"w",encoding="utf-8").write(html)
    print("Pagina creada: ~/nostr/campana.html")

async def main():
    sk=nsec_to_hex(open(os.path.join(DIR,"nsec.txt")).read().strip())
    arg=sys.argv[1] if len(sys.argv)>1 else "post"
    st=load()
    if arg=="page": page(); return
    if arg=="pin":
        if "last" not in st: print("Primero publica: python campaign.py post"); return
        print("Fijada" if await publish(build(sk,10001,"",[["e",st["last"]]])) else "Fallo")
        return
    text=NOTES[st["i"]%len(NOTES)].format(addr=ADDR)
    if GEYSER: text+="\n"+GEYSER
    ev=build(sk,1,text,[])
    if await publish(ev):
        st["i"]+=1; st["last"]=ev["id"]; save(st); print("Nota de campana publicada")
    else:
        print("No se publico en ningun relay")

asyncio.run(main())
