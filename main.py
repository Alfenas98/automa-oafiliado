"""
🤖 Bot de Afiliados ML — via REST API (sem scraping)
"""

import os
import json
import time
import math
import random
import requests
from datetime import datetime
from pathlib import Path

import config as cfg

ARQUIVO_HISTORICO   = "historico.json"
ARQUIVO_ESTATISTICAS = "estatisticas.json"


# ══════════════════════════════════════════════════════════════
# 💾 HISTÓRICO
# ══════════════════════════════════════════════════════════════

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

def ja_postado(produto_id, historico):
    return produto_id in historico

def registrar(produto_id, historico):
    if produto_id not in historico:
        historico.append(produto_id)
    if len(historico) > 2000:
        historico[:] = historico[-2000:]


# ══════════════════════════════════════════════════════════════
# 🧠 SCORE INTELIGENTE
# ══════════════════════════════════════════════════════════════

def calcular_score(produto):
    p = cfg.PESOS_SCORE
    s_desconto  = min(produto["desconto"] / 50, 1.0) * p["desconto"]
    av          = produto.get("avaliacao") or 0
    s_avaliacao = (av / 5.0) * p["avaliacao"]
    vendidos    = produto.get("vendidos") or 0
    s_vendidos  = (math.log10(max(vendidos, 1)) / 4) * p["vendidos"]
    s_frete     = p["frete_gratis"] if produto.get("frete_gratis") else 0
    s_loja      = p["loja_oficial"]  if produto.get("loja_oficial")  else 0
    return round(s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja, 1)


# ══════════════════════════════════════════════════════════════
# 🔍 MERCADO LIVRE — REST API (confiável, não bloqueia)
# ══════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AfiliadosBot/2.0)",
    "Accept":     "application/json",
}

def buscar_ml(busca, limite=20):
    query = (busca.get("q") or "oferta").strip()
    if not query:
        query = "oferta"

    url    = "https://api.mercadolibre.com/sites/MLB/search"
    params = {
        "q":         query,
        "sort":      "relevance",
        "limit":     limite,
        "condition": "new" if cfg.FILTROS_GLOBAIS.get("apenas_novo") else "all",
    }

    if busca.get("frete_gratis"):
        params["shipping_cost"] = "free"

    if busca.get("preco_min"):
        params["price_min"] = busca["preco_min"]
    if busca.get("preco_max"):
        params["price_max"] = busca["preco_max"]

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        resultados = r.json().get("results", [])
        print(f"   🌐 API retornou {len(resultados)} resultados para '{query}'")
    except Exception as e:
        print(f"   ❌ Erro na API ML: {e}")
        return []

    produtos = []
    for p in resultados:
        preco_original = p.get("original_price") or 0
        preco_atual    = p.get("price") or 0

        if preco_original <= 0 or preco_atual >= preco_original:
            continue

        desconto = int(((preco_original - preco_atual) / preco_original) * 100)

        if desconto < busca.get("desconto_min", 10):
            continue

        frete_info   = p.get("shipping") or {}
        frete_gratis = frete_info.get("free_shipping", False)
        loja_oficial = bool(p.get("official_store_id"))

        # Pega thumbnail em alta qualidade
        thumb = (p.get("thumbnail") or "").replace("http://", "https://")
        thumb = thumb.replace("-I.jpg", "-O.jpg")  # imagem maior

        produto = {
            "id":             str(p["id"]),
            "titulo":         p.get("title", ""),
            "preco_original": preco_original,
            "preco_atual":    preco_atual,
            "desconto":       desconto,
            "avaliacao":      0,
            "qtd_avaliacoes": 0,
            "vendidos":       p.get("sold_quantity") or 0,
            "frete_gratis":   frete_gratis,
            "loja_oficial":   loja_oficial,
            "thumbnail":      thumb,
            "url":            p.get("permalink", ""),
            "vendedor":       str((p.get("seller") or {}).get("id", "")),
            "categoria":      query,
        }
        produtos.append(produto)

    return produtos


def aplicar_filtros(produtos):
    f = cfg.FILTROS_GLOBAIS
    ok = []
    for p in produtos:
        titulo = p["titulo"].lower()
        if any(bl in titulo for bl in cfg.BLACKLIST_TITULO):
            continue
        if str(p["vendedor"]) in cfg.BLACKLIST_VENDEDOR:
            continue
        if p["vendidos"] < f.get("vendidos_min", 0):
            continue
        p["score"] = calcular_score(p)
        if p["score"] < f.get("score_minimo", 0):
            continue
        ok.append(p)
    return sorted(ok, key=lambda x: x["score"], reverse=True)


# ══════════════════════════════════════════════════════════════
# 🔗 LINK DE AFILIADO
# ══════════════════════════════════════════════════════════════

def gerar_link_afiliado(url):
    if cfg.AFILIADO_ID:
        return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}"
    return url


# ══════════════════════════════════════════════════════════════
# 💬 MENSAGENS
# ══════════════════════════════════════════════════════════════

HEADERS_MSG = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥",
    "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥",
    "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯",
    "💸 *PREÇO DESPENCOU* 💸",
    "🛒 *MELHOR PREÇO DO DIA* 🛒",
]

def fmt_preco(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_mensagem(p):
    titulo   = p["titulo"][:55] + ("..." if len(p["titulo"]) > 55 else "")
    original = fmt_preco(p["preco_original"])
    atual    = fmt_preco(p["preco_atual"])
    economia = fmt_preco(p["preco_original"] - p["preco_atual"])
    link     = p["link_afiliado"]
    header   = random.choice(HEADERS_MSG)

    linhas = [
        f"{header}\n",
        f"📦 *{titulo}*\n",
        f"~~{original}~~ → *{atual}*",
        f"💸 *{p['desconto']}% OFF* — economize *{economia}*\n",
    ]

    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",", "."))

    extras = []
    if p.get("frete_gratis"):
        extras.append("✅ Frete Grátis")
    if p.get("loja_oficial"):
        extras.append("🏪 Loja Oficial")
    if extras:
        linhas.append("   ".join(extras))

    linhas.append(f"\n👉 [*Garantir oferta agora*]({link})")
    linhas.append(f"\n_⏰ {datetime.now().strftime('%d/%m às %H:%M')} · Oferta por tempo limitado!_")

    return "\n".join(linhas)

def formatar_resumo(stats):
    return (
        f"📊 *Resumo do dia — {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        f"📦 Postados hoje: *{stats['postados']}*\n"
        f"🔍 Analisados: *{stats['analisados']}*\n"
        f"🚫 Filtrados: *{stats['filtrados']}*\n"
        f"💸 Maior desconto: *{stats['maior_desconto']}%*\n\n"
        f"_Mais ofertas amanhã cedo! 🌅_"
    )


# ══════════════════════════════════════════════════════════════
# 📤 TELEGRAM
# ══════════════════════════════════════════════════════════════

def enviar_telegram(texto, foto=""):
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        print("   ⚠️  Credenciais Telegram não configuradas!")
        return False

    base = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}"

    if foto:
        url     = f"{base}/sendPhoto"
        payload = {
            "chat_id":    cfg.CHANNEL_ID,
            "photo":      foto,
            "caption":    texto,
            "parse_mode": "Markdown",
        }
    else:
        url     = f"{base}/sendMessage"
        payload = {
            "chat_id":    cfg.CHANNEL_ID,
            "text":       texto,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            return True
        # Fallback: tenta sem foto
        if foto:
            r2 = requests.post(
                f"{base}/sendMessage",
                json={"chat_id": cfg.CHANNEL_ID, "text": texto, "parse_mode": "Markdown"},
                timeout=10
            )
            return r2.status_code == 200
        print(f"   ❌ Telegram erro {r.status_code}: {r.text[:120]}")
        return False
    except Exception as e:
        print(f"   ❌ Erro Telegram: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# ⏰ HORÁRIO
# ══════════════════════════════════════════════════════════════

def buscas_do_horario():
    hora = datetime.now().hour
    if   8  <= hora < 11: periodo = "manha"
    elif 11 <= hora < 14: periodo = "almoco"
    elif 14 <= hora < 18: periodo = "tarde"
    elif 18 <= hora < 21: periodo = "noite"
    else:                  periodo = "todas"

    cats = cfg.HORARIO_CATEGORIAS.get(periodo)
    if cats is None:
        return cfg.BUSCAS

    return [b for b in cfg.BUSCAS if (b.get("q") or "") in cats]


# ══════════════════════════════════════════════════════════════
# 🚀 MAIN
# ══════════════════════════════════════════════════════════════

def main():
    agora = datetime.now()
    print(f"\n{'═'*55}")
    print(f"  🤖 Bot Afiliados ML · {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*55}\n")

    historico    = carregar_json(ARQUIVO_HISTORICO, [])
    stats        = carregar_json(ARQUIVO_ESTATISTICAS, {
        "postados": 0, "analisados": 0,
        "filtrados": 0, "maior_desconto": 0,
        "data": agora.strftime("%d/%m/%Y")
    })

    if stats.get("data") != agora.strftime("%d/%m/%Y"):
        stats = {"postados": 0, "analisados": 0,
                 "filtrados": 0, "maior_desconto": 0,
                 "data": agora.strftime("%d/%m/%Y")}

    buscas      = buscas_do_horario()
    total_posts = 0

    print(f"  📋 Categorias nesta rodada: {len(buscas)}")
    print(f"  📦 Histórico: {len(historico)} produtos já postados\n")

    for busca in buscas:
        q = busca.get("q") or "oferta"
        print(f"  🔍 [{q.upper() or 'GERAL'}]  "
              f"R${busca.get('preco_min',0)}-R${busca.get('preco_max','∞')}  "
              f"≥{busca.get('desconto_min',0)}% off  "
              f"{'🚚 frete grátis' if busca.get('frete_gratis') else ''}")

        brutos    = buscar_ml(busca, limite=20)
        stats["analisados"] += len(brutos)

        filtrados = aplicar_filtros(brutos)
        descartados = len(brutos) - len(filtrados)
        stats["filtrados"] += descartados

        print(f"     ✅ {len(filtrados)} aprovados | 🚫 {descartados} descartados\n")

        postados_agora = 0
        for produto in filtrados:
            if postados_agora >= cfg.PRODUTOS_POR_BUSCA:
                break
            if ja_postado(produto["id"], historico):
                continue

            produto["link_afiliado"] = gerar_link_afiliado(produto["url"])
            mensagem = formatar_mensagem(produto)

            print(f"     📤 Score {produto['score']:5.1f} | "
                  f"{produto['desconto']}% off | "
                  f"R${produto['preco_atual']:.0f} | "
                  f"{produto['titulo'][:30]}...")

            ok = enviar_telegram(mensagem, produto["thumbnail"])

            if ok:
                registrar(produto["id"], historico)
                postados_agora += 1
                total_posts    += 1
                stats["postados"] += 1
                if produto["desconto"] > stats["maior_desconto"]:
                    stats["maior_desconto"] = produto["desconto"]
                print(f"     ✅ Enviado!")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)
            else:
                print(f"     ❌ Falha no envio")

        print()

    # Resumo diário às 21h
    if cfg.POSTAR_RESUMO_DIARIO and 21 <= agora.hour < 22:
        enviar_telegram(formatar_resumo(stats))
        print("  📊 Resumo diário enviado!\n")

    salvar_json(ARQUIVO_HISTORICO,    historico)
    salvar_json(ARQUIVO_ESTATISTICAS, stats)

    print(f"{'═'*55}")
    print(f"  ✅ Finalizado · {total_posts} post(s) enviados")
    print(f"  📈 Total do dia: {stats['postados']} posts")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
