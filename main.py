"""
Bot de Afiliados Mercado Livre - Versão Refatorada
- Renovação automática de token
- Filtros otimizados
- Melhor tratamento de erros
- Código mais limpo e profissional
"""

import json
import math
import random
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import config as cfg
import logging

# ===================== CONFIGURAÇÃO DE LOG =====================
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
    s = min(p.get("desconto", 0) / 50, 1.0) * pw["desconto"]
    s += (p.get("avaliacao", 0) / 5.0) * pw.get("avaliacao", 0.3)
    s += (math.log10(max(p.get("vendidos", 1), 1)) / 4) * pw.get("vendidos", 0.4)
    if p.get("frete_gratis"):
        s += pw.get("frete_gratis", 0.25)
    if p.get("loja_oficial"):
        s += pw.get("loja_oficial", 0.2)
    return round(s, 1)


# ===================== TOKEN MANAGEMENT =====================
def renovar_token():
    """Renova o access_token usando refresh_token"""
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
        refresh_token = dados.get("refresh_token", cfg.ML_REFRESH_TOKEN)
        expires_in = dados.get("expires_in", 21600)

        salvar_json(ARQUIVO_TOKEN, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in,
        })

        logger.info(f"✅ Token renovado com sucesso! Válido por {expires_in//3600}h")
        return access_token

    except Exception as e:
        logger.error(f"❌ Falha ao renovar token: {e}")
        logger.info("Usando token do config como fallback...")
        return cfg.ML_ACCESS_TOKEN


def obter_token():
    """Retorna token válido (cache ou renovado)"""
    cache = carregar_json(ARQUIVO_TOKEN, {})
    
    if cache.get("access_token") and cache.get("expires_at", 0) > time.time() + 900:  # 15 min margem
        logger.info("🔑 Usando token do cache")
        return cache["access_token"]
    
    return renovar_token()


# ===================== API MERCADO LIVRE =====================
def buscar_ml(busca: dict, token: str, limite: int = 50):
    params = {
        "q": busca.get("q", "oferta"),
        "limit": limite,
        "sort": busca.get("sort", "relevance"),
        "condition": "new",
    }

    # Filtros de preço
    preco_min = busca.get("preco_min")
    preco_max = busca.get("preco_max")
    if preco_min or preco_max:
        price_range = []
        if preco_min:
            price_range.append(str(preco_min))
        price_range.append(str(preco_max) if preco_max else "")
        params["price"] = "-".join(price_range)

    if busca.get("frete_gratis"):
        params["shipping"] = "free"

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
            timeout=15
        )
        r.raise_for_status()
        resultados = r.json().get("results", [])
        logger.info(f"📡 {len(resultados)} resultados para '{params['q']}'")
        return resultados
    except Exception as e:
        logger.error(f"Erro na API ML: {e}")
        return []


def processar_produto(p: dict, busca: dict) -> dict | None:
    """Processa e valida um produto cru da API"""
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
    seller = p.get("seller") or {}

    produto = {
        "id": str(p["id"]),
        "titulo": p.get("title", ""),
        "preco_original": orig,
        "preco_atual": atual,
        "desconto": desc,
        "avaliacao": 0,  # ML nem sempre retorna
        "vendidos": p.get("sold_quantity") or 0,
        "frete_gratis": shipping.get("free_shipping", False),
        "loja_oficial": bool(p.get("official_store_id")),
        "thumbnail": (p.get("thumbnail") or "").replace("http://", "https://").replace("-I.jpg", "-O.jpg"),
        "url": p.get("permalink", ""),
        "vendedor": str(seller.get("id", "")),
    }
    produto["score"] = calcular_score(produto)
    return produto


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


# ===================== MENSAGENS =====================
MSGS = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥", "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥", "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯", "💸 *PREÇO DESPENCOU* 💸",
]

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
    if ex:
        linhas.append(" ".join(ex))

    linhas.append(f"\n👉 [*Garantir oferta agora*]({p['link_afiliado']})")
    linhas.append(f"\n_⏰ {agora().strftime('%d/%m às %H:%M')} · Oferta por tempo limitado!_")

    return "\n".join(linhas)


def formatar_resumo(stats: dict) -> str:
    return (
        f"📊 *Resumo do dia — {agora().strftime('%d/%m/%Y')}*\n\n"
        f"📦 Postados: *{stats['postados']}*\n"
        f"🔍 Analisados: *{stats['analisados']}*\n"
        f"🚫 Filtrados: *{stats['filtrados']}*\n"
        f"💸 Maior desconto: *{stats['maior_desconto']}%*\n\n"
        f"_Bot rodando normalmente · Mais ofertas amanhã!_"
    )


# ===================== TELEGRAM =====================
def enviar_telegram(texto: str, foto: str = "") -> bool:
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        return False

    base = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}"
    try:
        if foto:
            r = requests.post(f"{base}/sendPhoto", json={
                "chat_id": cfg.CHANNEL_ID,
                "photo": foto,
                "caption": texto,
                "parse_mode": "Markdown"
            }, timeout=20)
        else:
            r = requests.post(f"{base}/sendMessage", json={
                "chat_id": cfg.CHANNEL_ID,
                "text": texto,
                "parse_mode": "Markdown"
            }, timeout=15)

        if r.status_code == 200:
            return True

        # Fallback
        if foto and r.status_code in (400, 413):
            logger.warning("Foto grande demais. Enviando apenas texto...")
            return enviar_telegram(texto)

        logger.error(f"Telegram {r.status_code}: {r.text[:100]}")
        return False

    except Exception as e:
        logger.error(f"Erro Telegram: {e}")
        return False


# ===================== MAIN =====================
def main():
    now = agora()
    logger.info("=" * 60)
    logger.info(f"🤖 Bot Afiliados ML Iniciado - {now.strftime('%d/%m/%Y %H:%M')} (Brasília)")
    logger.info("=" * 60)

    token = obter_token()
    historico_list = carregar_json(ARQUIVO_HISTORICO, [])
    historico_set = set(historico_list)

    stats = carregar_json(ARQUIVO_ESTATISTICAS, {
        "postados": 0, "analisados": 0, "filtrados": 0,
        "maior_desconto": 0, "data": now.strftime("%d/%m/%Y")
    })

    # Reset diário
    if stats.get("data") != now.strftime("%d/%m/%Y"):
        stats = {"postados": 0, "analisados": 0, "filtrados": 0,
                 "maior_desconto": 0, "data": now.strftime("%d/%m/%Y")}

    buscas = buscas_do_horario() if 'buscas_do_horario' in globals() else cfg.BUSCAS
    total_postados = 0

    for busca in buscas:
        q = busca.get("q", "oferta")
        logger.info(f"🔎 Buscando: {q.upper()} | {busca.get('preco_min',0)}-{busca.get('preco_max','∞')} | ≥{busca.get('desconto_min',0)}%")

        resultados = buscar_ml(busca, token)
        stats["analisados"] += len(resultados)

        produtos = []
        for r in resultados:
            prod = processar_produto(r, busca)
            if prod:
                produtos.append(prod)

        filtrados = aplicar_filtros(produtos, historico_set)
        stats["filtrados"] += len(produtos) - len(filtrados)

        logger.info(f"   → {len(filtrados)} produtos aprovados")

        for produto in filtrados[:cfg.PRODUTOS_POR_BUSCA]:
            produto["link_afiliado"] = f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={produto['url']}" if cfg.AFILIADO_ID else produto["url"]

            if enviar_telegram(formatar_mensagem(produto), produto["thumbnail"]):
                historico_set.add(produto["id"])
                historico_list.append(produto["id"])
                total_postados += 1
                stats["postados"] += 1

                if produto["desconto"] > stats["maior_desconto"]:
                    stats["maior_desconto"] = produto["desconto"]

                logger.info(f"✅ Postado | Score {produto['score']:.1f} | {produto['desconto']}% OFF")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)
            else:
                logger.warning("Falha ao enviar mensagem")

        # Limita tamanho do histórico
        if len(historico_list) > 2500:
            historico_list = historico_list[-2000:]
            historico_set = set(historico_list)

    # Resumo diário
    if cfg.POSTAR_RESUMO_DIARIO and 21 <= now.hour < 22:
        enviar_telegram(formatar_resumo(stats))

    salvar_json(ARQUIVO_HISTORICO, historico_list)
    salvar_json(ARQUIVO_ESTATISTICAS, stats)

    logger.info("=" * 60)
    logger.info(f"🏁 Finalizado! {total_postados} post(s) hoje | Total do dia: {stats['postados']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
