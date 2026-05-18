"""
Bot de Afiliados Mercado Livre - Versão Corrigida (Anti-403)
"""

import json
import math
import random
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging

# ===================== LOG =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ===================== ARQUIVOS =====================
ARQUIVO_HISTORICO = "historico.json"
ARQUIVO_ESTATISTICAS = "estatisticas.json"
ARQUIVO_TOKEN = "token_cache.json"

BRASILIA = timezone(timedelta(hours=-3))

def agora():
    return datetime.now(BRASILIA)

# ===================== UTILS =====================
def carregar_json(arquivo, default=None):
    if default is None:
        default = {}
    try:
        if Path(arquivo).exists():
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Erro ao carregar {arquivo}: {e}")
    return default


def salvar_json(arquivo, dados):
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar {arquivo}: {e}")


def calcular_score(p: dict) -> float:
    pw = cfg.PESOS_SCORE
    s = min(p.get("desconto", 0) / 50, 1.0) * pw.get("desconto", 0.35)
    s += (p.get("avaliacao", 0) / 5.0) * pw.get("avaliacao", 0.25)
    s += (math.log10(max(p.get("vendidos", 1), 1)) / 4) * pw.get("vendidos", 0.3)
    if p.get("frete_gratis"): s += pw.get("frete_gratis", 0.25)
    if p.get("loja_oficial"): s += pw.get("loja_oficial", 0.2)
    return round(s, 1)


# ===================== TOKEN =====================
def renovar_token():
    logger.info("🔄 Renovando access_token...")
    try:
        r = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": cfg.ML_CLIENT_ID,
                "client_secret": cfg.ML_CLIENT_SECRET,
                "refresh_token": cfg.ML_REFRESH_TOKEN,
            },
            timeout=15,
        )
        r.raise_for_status()
        dados = r.json()

        access_token = dados["access_token"]
        salvar_json(ARQUIVO_TOKEN, {
            "access_token": access_token,
            "refresh_token": dados.get("refresh_token", cfg.ML_REFRESH_TOKEN),
            "expires_at": time.time() + dados.get("expires_in", 21600),
        })
        logger.info("✅ Token renovado com sucesso!")
        return access_token
    except Exception as e:
        logger.error(f"Falha ao renovar token: {e}")
        return cfg.ML_ACCESS_TOKEN


def obter_token():
    cache = carregar_json(ARQUIVO_TOKEN, {})
    if cache.get("access_token") and cache.get("expires_at", 0) > time.time() + 900:
        logger.info("🔑 Usando token do cache")
        return cache["access_token"]
    return renovar_token()


# ===================== API ML (ANTI-403) =====================
def buscar_ml(busca: dict, token: str, limite: int = 50):
    q = busca.get("q", "oferta").strip()
    
    # Busca mínima para evitar 403
    params = {
        "q": q,
        "limit": min(limite, 50),
        "sort": busca.get("sort", "relevance"),
        "condition": "new",
    }

    # Preço (mantido, mas com cuidado)
    preco_min = busca.get("preco_min")
    preco_max = busca.get("preco_max")
    if preco_min or preco_max:
        pmin = str(preco_min) if preco_min else ""
        pmax = str(preco_max) if preco_max else ""
        params["price"] = f"{pmin}-{pmax}".strip("-")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        r = requests.get(
            "https://api.mercadolibre.com/sites/MLB/search",
            params=params,
            headers=headers,
            timeout=20
        )

        if r.status_code == 403:
            logger.warning(f"403 detectado. Tentando busca mínima para '{q}'...")
            r = requests.get(
                "https://api.mercadolibre.com/sites/MLB/search",
                params={"q": q, "limit": 50},
                headers=headers,
                timeout=15
            )

        r.raise_for_status()
        resultados = r.json().get("results", [])
        logger.info(f"📡 {len(resultados)} resultados para '{q}'")
        return resultados

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:150]}")
        return []
    except Exception as e:
        logger.error(f"Erro na API: {e}")
        return []


def processar_produto(p: dict, busca: dict) -> dict | None:
    orig = p.get("original_price") or 0
    atual = p.get("price") or 0
    if orig <= 0 or atual >= orig:
        return None

    desc = int(((orig - atual) / orig) * 100)
    if desc < busca.get("desconto_min", 10):
        return None

    if atual < busca.get("preco_min", 0) or atual > busca.get("preco_max", 999999):
        return None

    shipping = p.get("shipping") or {}
    if busca.get("frete_gratis", False) and not shipping.get("free_shipping", False):
        return None

    produto = {
        "id": str(p["id"]),
        "titulo": p.get("title", ""),
        "preco_original": orig,
        "preco_atual": atual,
        "desconto": desc,
        "vendidos": p.get("sold_quantity") or 0,
        "frete_gratis": shipping.get("free_shipping", False),
        "loja_oficial": bool(p.get("official_store_id")),
        "thumbnail": (p.get("thumbnail") or "").replace("http://","https://").replace("-I.jpg","-O.jpg"),
        "url": p.get("permalink", ""),
        "vendedor": str((p.get("seller") or {}).get("id", "")),
    }
    produto["score"] = calcular_score(produto)
    return produto


# ===================== FILTROS =====================
def aplicar_filtros(produtos: list, historico_set: set):
    ok = []
    for p in produtos:
        if p["id"] in historico_set:
            continue
        if any(bl in p["titulo"].lower() for bl in cfg.BLACKLIST_TITULO):
            continue
        if p["vendedor"] in cfg.BLACKLIST_VENDEDOR:
            continue
        if p["vendidos"] < cfg.FILTROS_GLOBAIS.get("vendidos_min", 0):
            continue
        if p["score"] < cfg.FILTROS_GLOBAIS.get("score_minimo", 0):
            continue
        ok.append(p)

    return sorted(ok, key=lambda x: x["score"], reverse=True)


# ===================== MENSAGENS E TELEGRAM =====================
MSGS = ["🔥 *OFERTA IMPERDÍVEL* 🔥", "⚡ *PROMOÇÃO RELÂMPAGO* ⚡", "💥 *DESCONTO ABSURDO* 💥",
        "🚨 *ALERTA DE OFERTA* 🚨", "🎯 *OPORTUNIDADE ÚNICA* 🎯"]

def fmt(v): 
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_mensagem(p: dict) -> str:
    titulo = p["titulo"][:58] + ("..." if len(p["titulo"]) > 58 else "")
    linhas = [
        f"{random.choice(MSGS)}\n",
        f"📦 *{titulo}*\n",
        f"~~{fmt(p['preco_original'])}~~ → *{fmt(p['preco_atual'])}*",
        f"💸 *{p['desconto']}% OFF* — economize *{fmt(p['preco_original']-p['preco_atual'])}*\n",
    ]
    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",", "."))
    
    ex = []
    if p.get("frete_gratis"): ex.append("✅ Frete Grátis")
    if p.get("loja_oficial"): ex.append("🏪 Loja Oficial")
    if ex: linhas.append(" ".join(ex))

    linhas.append(f"\n👉 [*Garantir oferta agora*]({p['link_afiliado']})")
    linhas.append(f"\n_⏰ {agora().strftime('%d/%m às %H:%M')} · Oferta limitada!_")
    return "\n".join(linhas)


def enviar_telegram(texto: str, foto: str = "") -> bool:
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        return False
    base = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}"
    try:
        if foto:
            r = requests.post(f"{base}/sendPhoto", json={
                "chat_id": cfg.CHANNEL_ID, "photo": foto,
                "caption": texto, "parse_mode": "Markdown"
            }, timeout=20)
        else:
            r = requests.post(f"{base}/sendMessage", json={
                "chat_id": cfg.CHANNEL_ID, "text": texto,
                "parse_mode": "Markdown"
            }, timeout=15)
        
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Erro Telegram: {e}")
        return False


# ===================== MAIN =====================
def main():
    now = agora()
    logger.info("=" * 65)
    logger.info(f"🤖 Bot Afiliados ML Iniciado - {now.strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 65)

    token = obter_token()
    historico_list = carregar_json(ARQUIVO_HISTORICO, [])
    historico_set = set(historico_list)

    stats = carregar_json(ARQUIVO_ESTATISTICAS, {"postados":0,"analisados":0,"filtrados":0,"maior_desconto":0,"data":now.strftime("%d/%m/%Y")})
    
    if stats.get("data") != now.strftime("%d/%m/%Y"):
        stats = {"postados":0,"analisados":0,"filtrados":0,"maior_desconto":0,"data":now.strftime("%d/%m/%Y")}

    buscas = cfg.BUSCAS  # ou sua função de horário

    total = 0
    for busca in buscas:
        q = busca.get("q", "oferta")
        logger.info(f"🔎 Buscando: {q.upper()} | R${busca.get('preco_min',0)} - R${busca.get('preco_max','∞')} | ≥{busca.get('desconto_min',0)}%")

        resultados = buscar_ml(busca, token)
        stats["analisados"] += len(resultados)

        produtos = [prod for r in resultados if (prod := processar_produto(r, busca))]
        filtrados = aplicar_filtros(produtos, historico_set)
        stats["filtrados"] += len(produtos) - len(filtrados)

        logger.info(f"   → {len(filtrados)} aprovados")

        for produto in filtrados[:cfg.PRODUTOS_POR_BUSCA]:
            produto["link_afiliado"] = f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={produto['url']}" if cfg.AFILIADO_ID else produto["url"]

            if enviar_telegram(formatar_mensagem(produto), produto["thumbnail"]):
                historico_set.add(produto["id"])
                historico_list.append(produto["id"])
                total += 1
                stats["postados"] += 1
                if produto["desconto"] > stats.get("maior_desconto", 0):
                    stats["maior_desconto"] = produto["desconto"]
                logger.info(f"✅ Postado | {produto['desconto']}% | Score {produto['score']:.1f}")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)

    salvar_json(ARQUIVO_HISTORICO, historico_list[-2000:])
    salvar_json(ARQUIVO_ESTATISTICAS, stats)

    logger.info("=" * 65)
    logger.info(f"🏁 Finalizado! {total} post(s) hoje")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
