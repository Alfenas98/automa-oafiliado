"""
Bot de Afiliados ML - versao definitiva
USA APENAS q + sort + limit na API. Tudo filtrado localmente. Sem 403.
"""

import json, math, random, time, requests
from datetime import datetime
from pathlib import Path
import config as cfg

ARQUIVO_HISTORICO    = "historico.json"
ARQUIVO_ESTATISTICAS = "estatisticas.json"

def carregar_json(arquivo, default):
    try:
        if Path(arquivo).exists():
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def ja_postado(pid, historico): return pid in historico

def registrar(pid, historico):
    if pid not in historico: historico.append(pid)
    if len(historico) > 2000: historico[:] = historico[-2000:]

def calcular_score(p):
    pw = cfg.PESOS_SCORE
    s  = min(p["desconto"]/50, 1.0) * pw["desconto"]
    s += (p.get("avaliacao", 0) / 5.0) * pw["avaliacao"]
    s += (math.log10(max(p.get("vendidos", 0), 1)) / 4) * pw["vendidos"]
    s += pw["frete_gratis"] if p.get("frete_gratis") else 0
    s += pw["loja_oficial"]  if p.get("loja_oficial")  else 0
    return round(s, 1)


# ══════════════════════════════════════════════════════
# API ML: SOMENTE q, sort, limit -> nunca retorna 403
# Todos os outros filtros sao aplicados localmente
# ══════════════════════════════════════════════════════

def buscar_ml(busca, limite=50):
    query = (busca.get("q") or "oferta").strip() or "oferta"
    try:
        r = requests.get(
            "https://api.mercadolibre.com/sites/MLB/search",
            params={"q": query, "sort": "relevance", "limit": limite},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15
        )
        r.raise_for_status()
        resultados = r.json().get("results", [])
        print(f"   API: {len(resultados)} resultados para '{query}'")
    except Exception as e:
        print(f"   ERRO API: {e}")
        return []

    preco_min    = busca.get("preco_min") or 0
    preco_max    = busca.get("preco_max") or 999999
    desconto_min = busca.get("desconto_min") or 10
    exige_frete  = busca.get("frete_gratis", False)
    apenas_novo  = cfg.FILTROS_GLOBAIS.get("apenas_novo", True)

    produtos = []
    for p in resultados:
        orig  = p.get("original_price") or 0
        atual = p.get("price") or 0
        if orig <= 0 or atual >= orig: continue

        desc = int(((orig - atual) / orig) * 100)
        if desc < desconto_min:                    continue
        if atual < preco_min or atual > preco_max: continue

        frete = (p.get("shipping") or {}).get("free_shipping", False)
        cond  = p.get("condition", "new")
        loja  = bool(p.get("official_store_id"))

        if apenas_novo and cond != "new": continue
        if exige_frete and not frete:     continue

        thumb = (p.get("thumbnail") or "").replace("http://","https://").replace("-I.jpg","-O.jpg")
        produtos.append({
            "id":             str(p["id"]),
            "titulo":         p.get("title", ""),
            "preco_original": orig,
            "preco_atual":    atual,
            "desconto":       desc,
            "avaliacao":      0,
            "vendidos":       p.get("sold_quantity") or 0,
            "frete_gratis":   frete,
            "loja_oficial":   loja,
            "thumbnail":      thumb,
            "url":            p.get("permalink", ""),
            "vendedor":       str((p.get("seller") or {}).get("id", "")),
        })
    return produtos

def aplicar_filtros(produtos):
    f, ok = cfg.FILTROS_GLOBAIS, []
    for p in produtos:
        if any(bl in p["titulo"].lower() for bl in cfg.BLACKLIST_TITULO): continue
        if str(p["vendedor"]) in cfg.BLACKLIST_VENDEDOR:                  continue
        if p["vendidos"] < f.get("vendidos_min", 0):                      continue
        p["score"] = calcular_score(p)
        if p["score"] < f.get("score_minimo", 0):                         continue
        ok.append(p)
    return sorted(ok, key=lambda x: x["score"], reverse=True)

def gerar_link(url):
    return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}" if cfg.AFILIADO_ID else url

MSGS = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥", "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥",  "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯","💸 *PREÇO DESPENCOU* 💸",
    "🛒 *MELHOR PREÇO DO DIA* 🛒",
]

def fmt(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def formatar_mensagem(p):
    titulo = p["titulo"][:55] + ("..." if len(p["titulo"]) > 55 else "")
    linhas = [
        f"{random.choice(MSGS)}\n",
        f"📦 *{titulo}*\n",
        f"~~{fmt(p['preco_original'])}~~ → *{fmt(p['preco_atual'])}*",
        f"💸 *{p['desconto']}% OFF* — economize *{fmt(p['preco_original']-p['preco_atual'])}*\n",
    ]
    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",","."))
    ex = []
    if p.get("frete_gratis"): ex.append("✅ Frete Grátis")
    if p.get("loja_oficial"):  ex.append("🏪 Loja Oficial")
    if ex: linhas.append("   ".join(ex))
    linhas.append(f"\n👉 [*Garantir oferta agora*]({p['link_afiliado']})")
    linhas.append(f"\n_⏰ {datetime.now().strftime('%d/%m às %H:%M')} · Oferta por tempo limitado!_")
    return "\n".join(linhas)

def formatar_resumo(stats):
    return (
        f"📊 *Resumo do dia — {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        f"📦 Postados: *{stats['postados']}*\n"
        f"🔍 Analisados: *{stats['analisados']}*\n"
        f"🚫 Filtrados: *{stats['filtrados']}*\n"
        f"💸 Maior desconto: *{stats['maior_desconto']}%*\n\n"
        f"_Mais ofertas amanhã! 🌅_"
    )

def enviar_telegram(texto, foto=""):
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID: return False
    base = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}"
    if foto:
        r = requests.post(f"{base}/sendPhoto",
            json={"chat_id": cfg.CHANNEL_ID, "photo": foto,
                  "caption": texto, "parse_mode": "Markdown"}, timeout=15)
    else:
        r = requests.post(f"{base}/sendMessage",
            json={"chat_id": cfg.CHANNEL_ID, "text": texto,
                  "parse_mode": "Markdown"}, timeout=15)
    if r.status_code == 200: return True
    if foto:
        r2 = requests.post(f"{base}/sendMessage",
            json={"chat_id": cfg.CHANNEL_ID, "text": texto,
                  "parse_mode": "Markdown"}, timeout=10)
        return r2.status_code == 200
    print(f"   Telegram {r.status_code}: {r.text[:80]}")
    return False

def buscas_do_horario():
    h    = datetime.now().hour
    p    = ("manha" if 8<=h<11 else "almoco" if 11<=h<14
            else "tarde" if 14<=h<18 else "noite" if 18<=h<21 else "todas")
    cats = cfg.HORARIO_CATEGORIAS.get(p)
    return cfg.BUSCAS if cats is None else [b for b in cfg.BUSCAS if (b.get("q") or "") in cats]

def main():
    agora = datetime.now()
    print(f"\n{'='*50}")
    print(f"  Bot Afiliados ML . {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")

    historico = carregar_json(ARQUIVO_HISTORICO, [])
    stats     = carregar_json(ARQUIVO_ESTATISTICAS, {
        "postados":0, "analisados":0, "filtrados":0,
        "maior_desconto":0, "data": agora.strftime("%d/%m/%Y")
    })
    if stats.get("data") != agora.strftime("%d/%m/%Y"):
        stats = {"postados":0, "analisados":0, "filtrados":0,
                 "maior_desconto":0, "data":agora.strftime("%d/%m/%Y")}

    buscas, total = buscas_do_horario(), 0
    print(f"  Categorias: {len(buscas)} | Historico: {len(historico)} produtos\n")

    for busca in buscas:
        q = busca.get("q") or "oferta"
        print(f"  [{q.upper()}]  R${busca.get('preco_min',0)}-"
              f"R${busca.get('preco_max','inf')}  >={busca.get('desconto_min',0)}% off")

        brutos      = buscar_ml(busca)
        stats["analisados"] += len(brutos)
        filtrados   = aplicar_filtros(brutos)
        descartados = len(brutos) - len(filtrados)
        stats["filtrados"] += descartados
        print(f"     {len(filtrados)} aprovados | {descartados} descartados\n")

        postados_agora = 0
        for produto in filtrados:
            if postados_agora >= cfg.PRODUTOS_POR_BUSCA: break
            if ja_postado(produto["id"], historico):     continue

            produto["link_afiliado"] = gerar_link(produto["url"])
            print(f"     Score {produto['score']:5.1f} | {produto['desconto']}% off | "
                  f"R${produto['preco_atual']:.0f} | {produto['titulo'][:30]}...")

            if enviar_telegram(formatar_mensagem(produto), produto["thumbnail"]):
                registrar(produto["id"], historico)
                postados_agora += 1
                total          += 1
                stats["postados"] += 1
                if produto["desconto"] > stats["maior_desconto"]:
                    stats["maior_desconto"] = produto["desconto"]
                print(f"     Enviado!")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)
            else:
                print(f"     Falha no envio")
        print()

    if cfg.POSTAR_RESUMO_DIARIO and 21 <= agora.hour < 22:
        enviar_telegram(formatar_resumo(stats))

    salvar_json(ARQUIVO_HISTORICO,    historico)
    salvar_json(ARQUIVO_ESTATISTICAS, stats)
    print(f"{'='*50}")
    print(f"  Finalizado . {total} post(s) | Total dia: {stats['postados']}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
