"""
🤖 Bot de Afiliados ML
Usa APP_USR access token com refresh automático via refresh_token.
"""

import json
import math
import random
import time
import requests
from datetime import datetime
from pathlib import Path

import config as cfg

ARQUIVO_HISTORICO    = "historico.json"
ARQUIVO_ESTATISTICAS = "estatisticas.json"
ARQUIVO_TOKEN        = "token_cache.json"


# ══════════════════════════════════════════════════════════════
# 💾 UTILITÁRIOS
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
# 🔑 TOKEN ML — com refresh automático
# ══════════════════════════════════════════════════════════════

def obter_token():
    """
    Tenta usar o access_token do config. Se expirado, renova com refresh_token.
    Salva o novo token em token_cache.json para próximas runs.
    """
    cache = carregar_json(ARQUIVO_TOKEN, {})

    # 1. Token em cache ainda válido?
    if cache.get("access_token") and cache.get("expires_at", 0) > time.time() + 300:
        print("  🔑 Token em cache (valido)")
        return cache["access_token"]

    # 2. Tenta o access_token fixo do config (pode já estar válido)
    token_cfg = cfg.ML_ACCESS_TOKEN
    if token_cfg:
        print("  🔑 Usando access_token do config")
        # Salva com validade de 6h para não testar desnecessariamente
        salvar_json(ARQUIVO_TOKEN, {
            "access_token":  token_cfg,
            "refresh_token": cfg.ML_REFRESH_TOKEN,
            "expires_at":    time.time() + 21600,
        })
        return token_cfg

    return None


def renovar_token(refresh_token):
    """Renova o access_token usando o refresh_token."""
    print("  🔄 Renovando token via refresh_token...")
    try:
        r = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "refresh_token",
                "client_id":     cfg.ML_CLIENT_ID,
                "client_secret": cfg.ML_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        r.raise_for_status()
        dados = r.json()
        novo_token   = dados["access_token"]
        novo_refresh = dados.get("refresh_token", refresh_token)
        expires_in   = dados.get("expires_in", 21600)

        salvar_json(ARQUIVO_TOKEN, {
            "access_token":  novo_token,
            "refresh_token": novo_refresh,
            "expires_at":    time.time() + expires_in,
        })

        print(f"  ✅ Token renovado! Valido por {expires_in // 3600}h")
        return novo_token
    except Exception as e:
        print(f"  ❌ Falha ao renovar token: {e}")
        return None


def buscar_com_token(url, params, token):
    """Faz requisição autenticada. Se 401, renova token e tenta de novo."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept":        "application/json",
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)

    if r.status_code == 401:
        print("  ⚠️  Token expirado, renovando...")
        cache         = carregar_json(ARQUIVO_TOKEN, {})
        refresh_token = cache.get("refresh_token") or cfg.ML_REFRESH_TOKEN
        novo_token    = renovar_token(refresh_token)
        if novo_token:
            headers["Authorization"] = f"Bearer {novo_token}"
            r = requests.get(url, params=params, headers=headers, timeout=15)

    r.raise_for_status()
    return r


# ══════════════════════════════════════════════════════════════
# 🧠 SCORE
# ══════════════════════════════════════════════════════════════

def calcular_score(p):
    pw          = cfg.PESOS_SCORE
    s_desconto  = min(p["desconto"] / 50, 1.0) * pw["desconto"]
    av          = p.get("avaliacao") or 0
    s_avaliacao = (av / 5.0) * pw["avaliacao"]
    vendidos    = p.get("vendidos") or 0
    s_vendidos  = (math.log10(max(vendidos, 1)) / 4) * pw["vendidos"]
    s_frete     = pw["frete_gratis"] if p.get("frete_gratis") else 0
    s_loja      = pw["loja_oficial"]  if p.get("loja_oficial")  else 0
    return round(s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja, 1)


# ══════════════════════════════════════════════════════════════
# 🔍 BUSCA ML — API autenticada com todos os filtros
# ══════════════════════════════════════════════════════════════

def buscar_ml(busca, token, limite=50):
    query = (busca.get("q") or "oferta").strip() or "oferta"

    params = {
        "q":             query,
        "sort":          "relevance",
        "limit":         limite,
        "condition":     "new" if cfg.FILTROS_GLOBAIS.get("apenas_novo") else "all",
        "shipping_cost": "free" if busca.get("frete_gratis") else None,
    }
    if busca.get("preco_min"): params["price_min"] = busca["preco_min"]
    if busca.get("preco_max"): params["price_max"] = busca["preco_max"]

    # Remove params None
    params = {k: v for k, v in params.items() if v is not None}

    try:
        r          = buscar_com_token("https://api.mercadolibre.com/sites/MLB/search", params, token)
        resultados = r.json().get("results", [])
        print(f"   🌐 API: {len(resultados)} resultados para '{query}'")
    except Exception as e:
        print(f"   ❌ Erro API ML: {e}")
        return []

    desconto_min = busca.get("desconto_min") or 10
    produtos = []

    for p in resultados:
        preco_original = p.get("original_price") or 0
        preco_atual    = p.get("price") or 0

        if preco_original <= 0 or preco_atual >= preco_original:
            continue

        desconto = int(((preco_original - preco_atual) / preco_original) * 100)
        if desconto < desconto_min:
            continue

        frete_info   = p.get("shipping") or {}
        frete_gratis = frete_info.get("free_shipping", False)
        loja_oficial = bool(p.get("official_store_id"))
        thumb        = (p.get("thumbnail") or "").replace("http://", "https://").replace("-I.jpg", "-O.jpg")

        produtos.append({
            "id":             str(p["id"]),
            "titulo":         p.get("title", ""),
            "preco_original": preco_original,
            "preco_atual":    preco_atual,
            "desconto":       desconto,
            "avaliacao":      0,
            "vendidos":       p.get("sold_quantity") or 0,
            "frete_gratis":   frete_gratis,
            "loja_oficial":   loja_oficial,
            "thumbnail":      thumb,
            "url":            p.get("permalink", ""),
            "vendedor":       str((p.get("seller") or {}).get("id", "")),
        })

    return produtos


def aplicar_filtros(produtos):
    f  = cfg.FILTROS_GLOBAIS
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
# 🔗 AFILIADO / 💬 MENSAGENS / 📤 TELEGRAM
# ══════════════════════════════════════════════════════════════

def gerar_link(url):
    if cfg.AFILIADO_ID:
        return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}"
    return url

HEADERS_MSG = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥", "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥",  "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯","💸 *PREÇO DESPENCOU* 💸",
    "🛒 *MELHOR PREÇO DO DIA* 🛒",
]

def fmt(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_mensagem(p):
    titulo  = p["titulo"][:55] + ("..." if len(p["titulo"]) > 55 else "")
    economia = fmt(p["preco_original"] - p["preco_atual"])
    linhas  = [
        f"{random.choice(HEADERS_MSG)}\n",
        f"📦 *{titulo}*\n",
        f"~~{fmt(p['preco_original'])}~~ → *{fmt(p['preco_atual'])}*",
        f"💸 *{p['desconto']}% OFF* — economize *{economia}*\n",
    ]
    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",", "."))
    extras = []
    if p.get("frete_gratis"): extras.append("✅ Frete Grátis")
    if p.get("loja_oficial"): extras.append("🏪 Loja Oficial")
    if extras: linhas.append("   ".join(extras))
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
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        print("   ⚠️  Credenciais Telegram ausentes!")
        return False
    base = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}"
    if foto:
        r = requests.post(f"{base}/sendPhoto", json={
            "chat_id": cfg.CHANNEL_ID, "photo": foto,
            "caption": texto, "parse_mode": "Markdown"
        }, timeout=15)
    else:
        r = requests.post(f"{base}/sendMessage", json={
            "chat_id": cfg.CHANNEL_ID, "text": texto, "parse_mode": "Markdown"
        }, timeout=15)
    if r.status_code == 200:
        return True
    if foto:
        r2 = requests.post(f"{base}/sendMessage", json={
            "chat_id": cfg.CHANNEL_ID, "text": texto, "parse_mode": "Markdown"
        }, timeout=10)
        return r2.status_code == 200
    print(f"   ❌ Telegram {r.status_code}: {r.text[:100]}")
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
    print(f"\n{'='*55}")
    print(f"  Bot Afiliados ML . {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}\n")

    token = obter_token()
    if not token:
        print("  ❌ Sem token ML — abortando")
        return

    historico = carregar_json(ARQUIVO_HISTORICO, [])
    stats     = carregar_json(ARQUIVO_ESTATISTICAS, {
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

    print(f"  Categorias: {len(buscas)} | Historico: {len(historico)} produtos\n")

    for busca in buscas:
        q = busca.get("q") or "oferta"
        print(f"  [{q.upper()}]  R${busca.get('preco_min',0)}-R${busca.get('preco_max','inf')}  >={busca.get('desconto_min',0)}% off")

        brutos      = buscar_ml(busca, token)
        stats["analisados"] += len(brutos)

        filtrados   = aplicar_filtros(brutos)
        descartados = len(brutos) - len(filtrados)
        stats["filtrados"] += descartados

        print(f"     {len(filtrados)} aprovados | {descartados} descartados\n")

        postados_agora = 0
        for produto in filtrados:
            if postados_agora >= cfg.PRODUTOS_POR_BUSCA:
                break
            if ja_postado(produto["id"], historico):
                continue

            produto["link_afiliado"] = gerar_link(produto["url"])
            mensagem = formatar_mensagem(produto)

            print(f"     Score {produto['score']:5.1f} | {produto['desconto']}% off | "
                  f"R${produto['preco_atual']:.0f} | {produto['titulo'][:30]}...")

            ok = enviar_telegram(mensagem, produto["thumbnail"])
            if ok:
                registrar(produto["id"], historico)
                postados_agora    += 1
                total_posts       += 1
                stats["postados"] += 1
                if produto["desconto"] > stats["maior_desconto"]:
                    stats["maior_desconto"] = produto["desconto"]
                print(f"     ✅ Enviado!")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)
            else:
                print(f"     ❌ Falha no envio")
        print()

    if cfg.POSTAR_RESUMO_DIARIO and 21 <= agora.hour < 22:
        enviar_telegram(formatar_resumo(stats))

    salvar_json(ARQUIVO_HISTORICO,    historico)
    salvar_json(ARQUIVO_ESTATISTICAS, stats)

    print(f"{'='*55}")
    print(f"  ✅ Finalizado . {total_posts} post(s) | Total dia: {stats['postados']}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
