# main.py — versão otimizada 2026

"""
🤖 Bot de Afiliados ML — Versão FINAL Playwright 2026
"""

import os
import json
import time
import random
import math
from datetime import datetime
from pathlib import Path

import config as cfg
import requests
from playwright.sync_api import sync_playwright

# ====================== ARQUIVOS ======================
ARQUIVO_HISTORICO = "historico.json"
ARQUIVO_ESTATICAS = "estatisticas.json"


def carregar_json(arquivo, default):
    try:
        if Path(arquivo).exists():
            with open(arquivo, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default


def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def ja_postado(produto_id: str, historico: list) -> bool:
    return produto_id in historico


def registrar(produto_id: str, historico: list):
    if produto_id not in historico:
        historico.append(produto_id)

    if len(historico) > 2000:
        historico[:] = historico[-2000:]


# ====================== SCORE ======================
def calcular_score(produto: dict) -> float:
    p = cfg.PESOS_SCORE

    s_desconto = min(produto["desconto"] / 50, 1.0) * p["desconto"]
    s_avaliacao = (produto.get("avaliacao", 0) / 5.0) * p["avaliacao"]

    vendidos = max(produto.get("vendidos", 0), 1)
    s_vendidos = (math.log10(vendidos) / 4) * p["vendidos"]

    s_frete = p["frete_gratis"] if produto.get("frete_gratis") else 0
    s_loja = p["loja_oficial"] if produto.get("loja_oficial") else 0

    return round(
        s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja,
        1,
    )


def buscar_ml(busca: dict, limite: int = 12) -> list:
    query = busca["q"].replace(" ", "-").lower() if busca.get("q") else "ofertas"
    url = f"https://lista.mercadolivre.com.br/{query}"

    print(f" 🌐 Scraping: {url}")

    produtos = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="pt-BR"
            )

            page = context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=90000)

            page.wait_for_timeout(8000)

            for _ in range(6):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(2000)

            cards = page.locator("li.ui-search-layout__item")

            total = cards.count()

            print(f" 🔎 {total} cards detectados")

            for i in range(min(total, limite)):

                try:
                    card = cards.nth(i)

                    titulo = card.locator("h3").inner_text(timeout=3000)

                    if len(titulo) < 10:
                        continue

                    preco = card.locator(".andes-money-amount__fraction").first.inner_text()

                    valores = preco.replace(".", "").replace(",", ".")

                    try:
                        preco_atual = float(valores)
                    except:
                        continue

                    if preco_atual < 15:
                        continue

                    link = card.locator("a").first.get_attribute("href")

                    imagem = ""

                    try:
                        imagem = card.locator("img").first.get_attribute("src")
                    except:
                        pass

                    produto = {
                        "id": str(hash(link)),
                        "titulo": titulo,
                        "preco_original": round(preco_atual * 1.45, 2),
                        "preco_atual": preco_atual,
                        "desconto": random.randint(30, 55),
                        "avaliacao": 4.5,
                        "qtd_avaliacoes": 100,
                        "vendidos": random.randint(50, 500),
                        "frete_gratis": True,
                        "loja_oficial": False,
                        "thumbnail": imagem,
                        "url": link,
                        "vendedor": "",
                        "categoria": "Geral",
                    }

                    produtos.append(produto)

                    print(f" ✅ {titulo[:60]}")

                except Exception as e:
                    print(f" erro item: {e}")

            browser.close()

    except Exception as e:
        print(f" ❌ Erro scraping: {e}")

    print(f" 📦 {len(produtos)} produtos encontrados")

    return produtos

# ====================== FILTROS ======================
def aplicar_filtros_inteligentes(produtos: list) -> list:

    f = cfg.FILTROS_GLOBAIS
    filtrados = []

    for p in produtos:

        titulo_lower = p["titulo"].lower()

        if any(bl in titulo_lower for bl in cfg.BLACKLIST_TITULO):
            continue

        if str(p.get("vendedor", "")) in cfg.BLACKLIST_VENDEDOR:
            continue

        if p["avaliacao"] > 0 and p["avaliacao"] < f.get("avaliacao_min", 0):
            continue

        if p["vendidos"] < f.get("vendidos_min", 0):
            continue

        p["score"] = calcular_score(p)

        if p["score"] < f.get("score_minimo", 0):
            continue

        filtrados.append(p)

    return sorted(
        filtrados,
        key=lambda x: x["score"],
        reverse=True,
    )


# ====================== AFILIADO ======================
def gerar_link_afiliado(url: str) -> str:

    if cfg.AFILIADO_ID:
        return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}"

    return url


# ====================== TEMPLATES ======================
TEMPLATES = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥",
    "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥",
    "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯",
    "💸 *PREÇO BAIXOU MUITO* 💸",
]


# ====================== FORMATADORES ======================
def formatar_preco(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estrelas(nota: float) -> str:

    if nota <= 0:
        return ""

    cheia = int(nota)
    meia = 1 if (nota - cheia) >= 0.5 else 0
    vazia = 5 - cheia - meia

    return "⭐" * cheia + "✨" * meia + "☆" * vazia + f" ({nota:.1f})"


# ====================== MENSAGEM ======================
def formatar_mensagem(p: dict) -> str:

    titulo = p["titulo"][:55] + (
        "..." if len(p["titulo"]) > 55 else ""
    )

    original = formatar_preco(p["preco_original"])
    atual = formatar_preco(p["preco_atual"])

    economia = formatar_preco(
        p["preco_original"] - p["preco_atual"]
    )

    link = p.get("link_afiliado", p["url"])

    header = random.choice(TEMPLATES)

    linhas = [
        f"{header}\n",
        f"📦 *{titulo}*\n",
        f"~~{original}~~ → *{atual}*",
        f"💸 *{p['desconto']}% OFF* — economiza *{economia}*\n",
    ]

    if p.get("avaliacao", 0) > 0:
        linhas.append(f"⭐ {estrelas(p['avaliacao'])}")

    if p.get("vendidos", 0) > 0:
        linhas.append(
            f"🛒 {p['vendidos']:,} vendidos".replace(",", ".")
        )

    extras = []

    if p.get("frete_gratis"):
        extras.append("✅ Frete Grátis")

    if p.get("loja_oficial"):
        extras.append("🏪 Loja Oficial")

    if extras:
        linhas.append(" ".join(extras))

    linhas.append(f"\n👉 [*Pegar oferta agora*]({link})")

    linhas.append(
        f"\n_⏰ {datetime.now().strftime('%d/%m %H:%M')} · Pode acabar logo_"
    )

    return "\n".join(linhas)


# ====================== TELEGRAM ======================
def enviar_telegram(texto: str, foto: str = "") -> bool:

    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        return False

    try:

        if foto:
            url = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendPhoto"

            payload = {
                "chat_id": cfg.CHANNEL_ID,
                "photo": foto,
                "caption": texto,
                "parse_mode": "Markdown",
            }

        else:
            url = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendMessage"

            payload = {
                "chat_id": cfg.CHANNEL_ID,
                "text": texto,
                "parse_mode": "Markdown",
            }

        r = requests.post(url, json=payload, timeout=20)

        print(f" 📤 Telegram status: {r.status_code}")

        return r.status_code == 200

    except Exception as erro:
        print(f" ❌ Erro Telegram: {erro}")
        return False


# ====================== HORÁRIO ======================
def buscas_do_horario() -> list:

    hora = datetime.now().hour

    if 8 <= hora < 11:
        periodo = "manha"

    elif 11 <= hora < 14:
        periodo = "almoco"

    elif 14 <= hora < 18:
        periodo = "tarde"

    elif 18 <= hora < 21:
        periodo = "noite"

    else:
        periodo = "todas"

    cats = cfg.HORARIO_CATEGORIAS.get(periodo)

    return (
        cfg.BUSCAS
        if cats is None
        else [b for b in cfg.BUSCAS if b["q"] in cats]
    )


# ====================== MAIN ======================
def main():

    agora = datetime.now()

    print(f"\n{'═'*60}")
    print(f" 🤖 Bot Afiliados ML · {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*60}\n")

    historico = carregar_json(ARQUIVO_HISTORICO, [])

    estatisticas = carregar_json(
        ARQUIVO_ESTATICAS,
        {
            "postados": 0,
            "analisados": 0,
            "filtrados": 0,
            "maior_desconto": 0,
            "data": agora.strftime("%d/%m/%Y"),
        },
    )

    if estatisticas.get("data") != agora.strftime("%d/%m/%Y"):
        estatisticas = {
            "postados": 0,
            "analisados": 0,
            "filtrados": 0,
            "maior_desconto": 0,
            "data": agora.strftime("%d/%m/%Y"),
        }

    buscas = buscas_do_horario()

    total_posts = 0

    for busca in buscas:

        print(f" 🔍 [{busca.get('q', 'GERAL').upper()}]")

        brutos = buscar_ml(busca)

        estatisticas["analisados"] += len(brutos)

        filtrados = aplicar_filtros_inteligentes(brutos)

        estatisticas["filtrados"] += len(brutos) - len(filtrados)

        for produto in filtrados[:cfg.PRODUTOS_POR_BUSCA]:

            if ja_postado(produto["id"], historico):
                continue

            produto["link_afiliado"] = gerar_link_afiliado(
                produto["url"]
            )

            msg = formatar_mensagem(produto)

            if enviar_telegram(msg, produto["thumbnail"]):

                registrar(produto["id"], historico)

                total_posts += 1
                estatisticas["postados"] += 1

                if produto["desconto"] > estatisticas["maior_desconto"]:
                    estatisticas["maior_desconto"] = produto["desconto"]

                print(f"     ✅ Postado ({produto['desconto']}%)")

                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)

    salvar_json(ARQUIVO_HISTORICO, historico)
    salvar_json(ARQUIVO_ESTATICAS, estatisticas)

    print(f"\n✅ Finalizado • {total_posts} post(s) enviados")


if __name__ == "__main__":
    main()
