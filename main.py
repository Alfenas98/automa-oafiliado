"""
🤖 Bot de Afiliados ML — Versão Inteligente
Filtragem por score, qualidade, horário e muito mais.
"""

import os
import sys
import json
import time
import random
import requests
from datetime import datetime
from pathlib import Path

import config as cfg


# ══════════════════════════════════════════════════════════════
# 💾 HISTÓRICO
# ══════════════════════════════════════════════════════════════

ARQUIVO_HISTORICO  = "historico.json"
ARQUIVO_ESTATICAS  = "estatisticas.json"

def carregar_json(arquivo, default):
    try:
        if Path(arquivo).exists():
            with open(arquivo) as f:
                return json.load(f)
    except Exception:
        pass
    return default

def salvar_json(arquivo, dados):
    with open(arquivo, "w") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def ja_postado(produto_id: str, historico: list) -> bool:
    return produto_id in historico

def registrar(produto_id: str, historico: list):
    if produto_id not in historico:
        historico.append(produto_id)
    # Mantém só os últimos 2000 IDs para não crescer infinito
    if len(historico) > 2000:
        historico[:] = historico[-2000:]


# ══════════════════════════════════════════════════════════════
# 🧠 SCORE INTELIGENTE
# ══════════════════════════════════════════════════════════════

def calcular_score(produto: dict) -> float:
    """
    Calcula um score de 0 a 100 baseado em múltiplos fatores.
    Quanto maior, mais vale a pena postar.
    """
    p = cfg.PESOS_SCORE

    # 1. Desconto (0-100): desconto de 50%+ já vale 100 pontos
    s_desconto = min(produto["desconto"] / 50, 1.0) * p["desconto"]

    # 2. Avaliação (0-5 → 0-100)
    av = produto.get("avaliacao", 0) or 0
    s_avaliacao = (av / 5.0) * p["avaliacao"]

    # 3. Vendidos (escala logarítmica: 1-10k)
    vendidos = produto.get("vendidos", 0) or 0
    import math
    s_vendidos = (math.log10(max(vendidos, 1)) / 4) * p["vendidos"]  # log10(10000)=4

    # 4. Frete grátis (binário)
    s_frete = p["frete_gratis"] if produto.get("frete_gratis") else 0

    # 5. Loja oficial (binário)
    s_loja = p["loja_oficial"] if produto.get("loja_oficial") else 0

    total = s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja
    return round(total, 1)


# ══════════════════════════════════════════════════════════════
# 🔍 MERCADO LIVRE API
# ══════════════════════════════════════════════════════════════

def buscar_ml(busca: dict, limite: int = 20) -> list:
    """Busca produtos na API pública do ML com todos os filtros."""

    url    = "https://api.mercadolibre.com/sites/MLB/search"
    params = {
        "q":         busca["q"],
        "sort":      "relevance",
        "limit":     limite,
        "condition": "new" if cfg.FILTROS_GLOBAIS.get("apenas_novo") else "all",
    }

    # Frete grátis direto na API
    if busca.get("frete_gratis"):
        params["shipping_cost"] = "free"

    # Loja oficial direto na API
    if cfg.FILTROS_GLOBAIS.get("loja_oficial"):
        params["official_store"] = "yes"

    # Faixa de preço
    if busca.get("preco_min"):
        params["price_min"] = busca["preco_min"]
    if busca.get("preco_max"):
        params["price_max"] = busca["preco_max"]

    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        resultados = r.json().get("results", [])
    except Exception as e:
        print(f"   ❌ Erro na API: {e}")
        return []

    produtos = []
    for p in resultados:
        preco_original = p.get("original_price") or 0
        preco_atual    = p.get("price", 0)

        # Ignora sem preço original (sem desconto real)
        if preco_original <= 0 or preco_atual >= preco_original:
            continue

        desconto = int(((preco_original - preco_atual) / preco_original) * 100)

        # Filtro de desconto mínimo (por categoria)
        if desconto < busca.get("desconto_min", 10):
            continue

        # Dados de avaliação
        av_dados    = p.get("reviews", {}) or {}
        avaliacao   = float(av_dados.get("rating_average", 0) or 0)
        qtd_aval    = int(av_dados.get("total", 0) or 0)

        # Frete grátis
        frete_info  = p.get("shipping", {}) or {}
        frete_gratis = frete_info.get("free_shipping", False)

        # Loja oficial
        loja_oficial = bool(p.get("official_store_id"))

        produto = {
            "id":              str(p["id"]),
            "titulo":          p.get("title", ""),
            "preco_original":  preco_original,
            "preco_atual":     preco_atual,
            "desconto":        desconto,
            "avaliacao":       avaliacao,
            "qtd_avaliacoes":  qtd_aval,
            "vendidos":        p.get("sold_quantity", 0) or 0,
            "frete_gratis":    frete_gratis,
            "loja_oficial":    loja_oficial,
            "thumbnail":       (p.get("thumbnail") or "").replace("http://", "https://"),
            "url":             p.get("permalink", ""),
            "vendedor":        p.get("seller", {}).get("id", ""),
            "categoria":       busca["q"],
        }

        produtos.append(produto)

    return produtos


def aplicar_filtros_inteligentes(produtos: list) -> list:
    """Aplica filtros globais de qualidade e blacklist."""
    f       = cfg.FILTROS_GLOBAIS
    filtrados = []

    for p in produtos:
        titulo_lower = p["titulo"].lower()

        # Blacklist de palavras no título
        if any(bl in titulo_lower for bl in cfg.BLACKLIST_TITULO):
            continue

        # Blacklist de vendedores
        if str(p["vendedor"]) in cfg.BLACKLIST_VENDEDOR:
            continue

        # Avaliação mínima (ignora produtos sem avaliação se tiver vendas suficientes)
        if p["avaliacao"] > 0 and p["avaliacao"] < f.get("avaliacao_min", 0):
            continue

        # Mínimo de vendas
        if p["vendidos"] < f.get("vendidos_min", 0):
            continue

        # Score mínimo
        p["score"] = calcular_score(p)
        if p["score"] < f.get("score_minimo", 0):
            continue

        filtrados.append(p)

    # Ordena pelo score (melhor primeiro)
    return sorted(filtrados, key=lambda x: x["score"], reverse=True)


# ══════════════════════════════════════════════════════════════
# 🔗 LINK DE AFILIADO
# ══════════════════════════════════════════════════════════════

def gerar_link_afiliado(url: str) -> str:
    if cfg.AFILIADO_ID:
        return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}"
    return url


# ══════════════════════════════════════════════════════════════
# 💬 FORMATAÇÃO DAS MENSAGENS
# Usa templates variados para não parecer robótico
# ══════════════════════════════════════════════════════════════

TEMPLATES = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥",
    "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥",
    "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯",
    "💸 *PREÇO BAIXOU MUITO* 💸",
]

def formatar_preco(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def estrelas(nota: float) -> str:
    if nota <= 0:
        return ""
    cheia = int(nota)
    meia  = 1 if (nota - cheia) >= 0.5 else 0
    vazia = 5 - cheia - meia
    return "⭐" * cheia + "✨" * meia + "☆" * vazia + f" ({nota:.1f})"

def formatar_mensagem(p: dict) -> str:
    titulo    = p["titulo"][:55] + ("..." if len(p["titulo"]) > 55 else "")
    original  = formatar_preco(p["preco_original"])
    atual     = formatar_preco(p["preco_atual"])
    economia  = formatar_preco(p["preco_original"] - p["preco_atual"])
    desconto  = p["desconto"]
    link      = p["link_afiliado"]
    header    = random.choice(TEMPLATES)

    linhas = [
        f"{header}\n",
        f"📦 *{titulo}*\n",
        f"~~{original}~~ → *{atual}*",
        f"💸 *{desconto}% OFF* — você economiza *{economia}*\n",
    ]

    if p.get("avaliacao", 0) > 0:
        linhas.append(f"⭐ {estrelas(p['avaliacao'])} ({p.get('qtd_avaliacoes', 0)} avaliações)")

    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",", "."))

    extras = []
    if p.get("frete_gratis"):
        extras.append("✅ Frete Grátis")
    if p.get("loja_oficial"):
        extras.append("🏪 Loja Oficial")
    if extras:
        linhas.append("   ".join(extras))

    linhas.append(f"\n👉 [*Pegar oferta agora*]({link})")
    linhas.append(f"\n_⏰ {datetime.now().strftime('%d/%m às %H:%M')} · Pode acabar a qualquer momento_")

    return "\n".join(linhas)

def formatar_resumo_diario(stats: dict) -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return (
        f"📊 *Resumo do dia — {hoje}*\n\n"
        f"📦 Produtos postados: *{stats['postados']}*\n"
        f"🔍 Produtos analisados: *{stats['analisados']}*\n"
        f"🚫 Filtrados por qualidade: *{stats['filtrados']}*\n"
        f"💸 Maior desconto do dia: *{stats['maior_desconto']}%*\n\n"
        f"_Próximas ofertas amanhã cedo! 🌅_"
    )


# ══════════════════════════════════════════════════════════════
# 📤 TELEGRAM
# ══════════════════════════════════════════════════════════════

def enviar_telegram(texto: str, foto: str = "") -> bool:
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        print("   ⚠️  Credenciais Telegram não configuradas")
        return False

    if foto:
        url     = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id":    cfg.CHANNEL_ID,
            "photo":      foto,
            "caption":    texto,
            "parse_mode": "Markdown",
        }
    else:
        url     = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id":    cfg.CHANNEL_ID,
            "text":       texto,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

    try:
        r = requests.post(url, json=payload, timeout=12)
        if r.status_code == 200:
            return True
        # Se falhou com foto, tenta só texto
        if foto and r.status_code != 200:
            payload2 = {"chat_id": cfg.CHANNEL_ID, "text": texto, "parse_mode": "Markdown"}
            r2 = requests.post(
                f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendMessage",
                json=payload2, timeout=10
            )
            return r2.status_code == 200
        print(f"   ❌ Telegram {r.status_code}: {r.text[:100]}")
        return False
    except Exception as e:
        print(f"   ❌ Erro Telegram: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# ⏰ SELEÇÃO POR HORÁRIO
# ══════════════════════════════════════════════════════════════

def buscas_do_horario() -> list:
    """Retorna as buscas apropriadas para o horário atual."""
    hora = datetime.now().hour

    if   8  <= hora < 11: periodo = "manha"
    elif 11 <= hora < 14: periodo = "almoco"
    elif 14 <= hora < 18: periodo = "tarde"
    elif 18 <= hora < 21: periodo = "noite"
    else:                  periodo = "todas"

    categorias_periodo = cfg.HORARIO_CATEGORIAS.get(periodo)

    if categorias_periodo is None:
        return cfg.BUSCAS  # todas

    return [b for b in cfg.BUSCAS if b["q"] in categorias_periodo]


# ══════════════════════════════════════════════════════════════
# 🚀 EXECUÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    agora = datetime.now()
    print(f"\n{'═'*55}")
    print(f"  🤖 Bot Afiliados ML · {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*55}\n")

    # Carrega dados persistentes
    historico  = carregar_json(ARQUIVO_HISTORICO, [])
    estatisticas = carregar_json(ARQUIVO_ESTATICAS, {
        "postados": 0, "analisados": 0,
        "filtrados": 0, "maior_desconto": 0,
        "data": agora.strftime("%d/%m/%Y")
    })

    # Reseta estatísticas se for novo dia
    if estatisticas.get("data") != agora.strftime("%d/%m/%Y"):
        estatisticas = {
            "postados": 0, "analisados": 0,
            "filtrados": 0, "maior_desconto": 0,
            "data": agora.strftime("%d/%m/%Y")
        }

    buscas     = buscas_do_horario()
    total_posts = 0

    print(f"  📋 Categorias nesta rodada: {len(buscas)}")
    print(f"  📦 Histórico: {len(historico)} produtos já postados\n")

    for busca in buscas:
        print(f"  🔍 [{busca['q'].upper()}]  "
              f"R${busca.get('preco_min',0)}-R${busca.get('preco_max','∞')}  "
              f"≥{busca.get('desconto_min',0)}% off")

        # 1. Busca na API
        brutos = buscar_ml(busca, limite=20)
        estatisticas["analisados"] += len(brutos)

        # 2. Filtros inteligentes
        filtrados = aplicar_filtros_inteligentes(brutos)
        descartados = len(brutos) - len(filtrados)
        estatisticas["filtrados"] += descartados

        print(f"     📊 {len(brutos)} encontrados → {filtrados and len(filtrados) or 0} aprovados "
              f"({descartados} descartados pelos filtros)")

        postados_agora = 0
        for produto in filtrados:
            if postados_agora >= cfg.PRODUTOS_POR_BUSCA:
                break
            if ja_postado(produto["id"], historico):
                continue

            # Gera link e formata
            produto["link_afiliado"] = gerar_link_afiliado(produto["url"])
            mensagem = formatar_mensagem(produto)

            print(f"     📤 Score {produto['score']:5.1f} | "
                  f"{produto['desconto']}% off | "
                  f"{produto['titulo'][:35]}...")

            ok = enviar_telegram(mensagem, produto["thumbnail"])

            if ok:
                registrar(produto["id"], historico)
                postados_agora += 1
                total_posts += 1
                estatisticas["postados"] += 1
                if produto["desconto"] > estatisticas["maior_desconto"]:
                    estatisticas["maior_desconto"] = produto["desconto"]
                print(f"     ✅ Enviado!")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)
            else:
                print(f"     ❌ Falha no envio")

        print()

    # Resumo diário (só na última rodada do dia, ~21h)
    if cfg.POSTAR_RESUMO_DIARIO and 21 <= agora.hour < 22:
        resumo = formatar_resumo_diario(estatisticas)
        enviar_telegram(resumo)
        print("  📊 Resumo diário enviado!\n")

    # Salva histórico e estatísticas
    salvar_json(ARQUIVO_HISTORICO, historico)
    salvar_json(ARQUIVO_ESTATICAS, estatisticas)

    print(f"{'═'*55}")
    print(f"  ✅ Rodada concluída · {total_posts} post(s) enviado(s)")
    print(f"  📈 Total do dia: {estatisticas['postados']} posts")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
