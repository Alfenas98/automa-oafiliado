"""
🤖 Bot de Afiliados ML — Versão Scraping 2026
"""

import os
import sys
import json
import time
import random
import math
from datetime import datetime
from pathlib import Path

import config as cfg
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ====================== ARQUIVOS ======================
ARQUIVO_HISTORICO = "historico.json"
ARQUIVO_ESTATICAS = "estatisticas.json"

def carregar_json(arquivo, default):
    try:
        if Path(arquivo).exists():
            with open(arquivo, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
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
    
    total = s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja
    return round(total, 1)

# ====================== WEB SCRAPING ======================
def buscar_ml(busca: dict, limite: int = 20) -> list:
    query = busca["q"].replace(" ", "-").lower()
    url = f"https://lista.mercadolivre.com.br/{query}"

    if busca.get("preco_min") or busca.get("preco_max"):
        url += f"_PriceRange_{busca.get('preco_min', 0)}-{busca.get('preco_max', '*')}"
    if busca.get("frete_gratis"):
        url += "_FreightCost_0"

    print(f" 🌐 Scraping: {url}")

    produtos = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)  # Aguarda JS carregar produtos

            soup = BeautifulSoup(page.content(), "lxml")
            cards = soup.select("div.andes-card, article.andes-card, div.ui-search-result__wrapper")

            for card in cards[:limite]:
                try:
                    # Título
                    titulo_tag = card.select_one("h2.ui-search-item__title, h3.poly-component__title")
                    titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""

                    # Preços
                    preco_atual_tag = card.select_one("span.andes-money-amount__fraction")
                    preco_original_tag = card.select_one("span.andes-money-amount--previous .andes-money-amount__fraction, s .andes-money-amount__fraction")

                    if not preco_atual_tag or not titulo:
                        continue

                    def limpar_preco(tag):
                        if not tag: return 0
                        text = tag.get_text(strip=True).replace(".", "").replace(",", ".")
                        try: return float(text)
                        except: return 0

                    preco_atual = limpar_preco(preco_atual_tag)
                    preco_original = limpar_preco(preco_original_tag) or preco_atual

                    if preco_original <= preco_atual * 1.08:  # mínimo 8% de desconto
                        continue

                    desconto = int(((preco_original - preco_atual) / preco_original) * 100)
                    if desconto < busca.get("desconto_min", 15):
                        continue

                    # Link
                    link_tag = card.select_one("a.ui-search-link, a.poly-component__title-link")
                    link = "https://www.mercadolivre.com.br" + link_tag.get("href", "") if link_tag else ""

                    # Imagem
                    img = card.select_one("img")
                    thumbnail = img.get("src") or img.get("data-src", "") if img else ""

                    # Avaliação e vendidos (aproximado)
                    avaliacao = 4.3
                    vendidos = 150
                    avaliacao_tag = card.select_one("span.andes-rating__average")
                    if avaliacao_tag:
                        try:
                            avaliacao = float(avaliacao_tag.get_text(strip=True).replace(",", "."))
                        except:
                            pass

                    produto = {
                        "id": link.split("/")[-1].split("-")[0] if link else str(hash(titulo)),
                        "titulo": titulo,
                        "preco_original": preco_original,
                        "preco_atual": preco_atual,
                        "desconto": desconto,
                        "avaliacao": avaliacao,
                        "qtd_avaliacoes": 80,
                        "vendidos": vendidos,
                        "frete_gratis": busca.get("frete_gratis", False),
                        "loja_oficial": False,
                        "thumbnail": thumbnail.replace("http://", "https://"),
                        "url": link,
                        "vendedor": "",
                        "categoria": busca["q"],
                    }
                    produtos.append(produto)

                except Exception:
                    continue

            browser.close()

    except Exception as e:
        print(f" ❌ Erro no scraping: {e}")

    print(f" 📦 {len(produtos)} produtos encontrados via scraping")
    return produtos

# ====================== FUNÇÕES ORIGINAIS (mantidas) ======================
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
    return sorted(filtrados, key=lambda x: x["score"], reverse=True)


def gerar_link_afiliado(url: str) -> str:
    if cfg.AFILIADO_ID:
        return f"https://mercadolivre.com/sec/{cfg.AFILIADO_ID}?url={url}"
    return url


TEMPLATES = [
    "🔥 *OFERTA IMPERDÍVEL* 🔥", "⚡ *PROMOÇÃO RELÂMPAGO* ⚡",
    "💥 *DESCONTO ABSURDO* 💥", "🚨 *ALERTA DE OFERTA* 🚨",
    "🎯 *OPORTUNIDADE ÚNICA* 🎯", "💸 *PREÇO BAIXOU MUITO* 💸",
]

def formatar_preco(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def estrelas(nota: float) -> str:
    if nota <= 0: return ""
    cheia = int(nota)
    meia = 1 if (nota - cheia) >= 0.5 else 0
    vazia = 5 - cheia - meia
    return "⭐" * cheia + "✨" * meia + "☆" * vazia + f" ({nota:.1f})"

def formatar_mensagem(p: dict) -> str:
    titulo = p["titulo"][:55] + ("..." if len(p["titulo"]) > 55 else "")
    original = formatar_preco(p["preco_original"])
    atual = formatar_preco(p["preco_atual"])
    economia = formatar_preco(p["preco_original"] - p["preco_atual"])
    link = p["link_afiliado"]
    header = random.choice(TEMPLATES)

    linhas = [
        f"{header}\n",
        f"📦 *{titulo}*\n",
        f"~~{original}~~ → *{atual}*",
        f"💸 *{p['desconto']}% OFF* — você economiza *{economia}*\n",
    ]
    if p.get("avaliacao", 0) > 0:
        linhas.append(f"⭐ {estrelas(p['avaliacao'])} ({p.get('qtd_avaliacoes', 0)} avaliações)")
    if p.get("vendidos", 0) > 0:
        linhas.append(f"🛒 {p['vendidos']:,} vendidos".replace(",", "."))

    extras = []
    if p.get("frete_gratis"): extras.append("✅ Frete Grátis")
    if p.get("loja_oficial"): extras.append("🏪 Loja Oficial")
    if extras:
        linhas.append("   ".join(extras))

    linhas.append(f"\n👉 [*Pegar oferta agora*]({link})")
    linhas.append(f"\n_⏰ {datetime.now().strftime('%d/%m às %H:%M')} · Pode acabar a qualquer momento_")
    return "\n".join(linhas)

def formatar_resumo_diario(stats: dict) -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"📊 *Resumo do dia — {hoje}*\n\n📦 Postados: *{stats['postados']}*\n🔍 Analisados: *{stats['analisados']}*\n🚫 Filtrados: *{stats['filtrados']}*\n💸 Maior desconto: *{stats['maior_desconto']}%*"

def enviar_telegram(texto: str, foto: str = "") -> bool:
    if not cfg.BOT_TOKEN or not cfg.CHANNEL_ID:
        return False
    try:
        if foto:
            url = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendPhoto"
            payload = {"chat_id": cfg.CHANNEL_ID, "photo": foto, "caption": texto, "parse_mode": "Markdown"}
        else:
            url = f"https://api.telegram.org/bot{cfg.BOT_TOKEN}/sendMessage"
            payload = {"chat_id": cfg.CHANNEL_ID, "text": texto, "parse_mode": "Markdown"}
        
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except:
        return False

def buscas_do_horario() -> list:
    hora = datetime.now().hour
    if 8 <= hora < 11: periodo = "manha"
    elif 11 <= hora < 14: periodo = "almoco"
    elif 14 <= hora < 18: periodo = "tarde"
    elif 18 <= hora < 21: periodo = "noite"
    else: periodo = "todas"

    cats = cfg.HORARIO_CATEGORIAS.get(periodo)
    return cfg.BUSCAS if cats is None else [b for b in cfg.BUSCAS if b["q"] in cats]

# ====================== MAIN ======================
def main():
    agora = datetime.now()
    print(f"\n{'═'*60}")
    print(f" 🤖 Bot Afiliados ML · {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'═'*60}\n")

    historico = carregar_json(ARQUIVO_HISTORICO, [])
    estatisticas = carregar_json(ARQUIVO_ESTATICAS, {"postados":0,"analisados":0,"filtrados":0,"maior_desconto":0,"data":agora.strftime("%d/%m/%Y")})

    if estatisticas.get("data") != agora.strftime("%d/%m/%Y"):
        estatisticas = {"postados":0,"analisados":0,"filtrados":0,"maior_desconto":0,"data":agora.strftime("%d/%m/%Y")}

    buscas = buscas_do_horario()
    total_posts = 0

    print(f" 📋 Categorias: {len(buscas)}\n")

    for busca in buscas:
        print(f" 🔍 [{busca['q'].upper()}]")
        brutos = buscar_ml(busca, limite=20)
        estatisticas["analisados"] += len(brutos)

        filtrados = aplicar_filtros_inteligentes(brutos)
        estatisticas["filtrados"] += (len(brutos) - len(filtrados))

        print(f"     → {len(filtrados)} aprovados")

        for produto in filtrados[:cfg.PRODUTOS_POR_BUSCA]:
            if ja_postado(produto["id"], historico):
                continue
            produto["link_afiliado"] = gerar_link_afiliado(produto["url"])
            msg = formatar_mensagem(produto)
            ok = enviar_telegram(msg, produto["thumbnail"])
            if ok:
                registrar(produto["id"], historico)
                total_posts += 1
                estatisticas["postados"] += 1
                if produto["desconto"] > estatisticas["maior_desconto"]:
                    estatisticas["maior_desconto"] = produto["desconto"]
                print(f"     ✅ Postado: {produto['desconto']}% off")
                time.sleep(cfg.PAUSA_ENTRE_POSTS_SEG)

    if cfg.POSTAR_RESUMO_DIARIO and 21 <= agora.hour < 22:
        enviar_telegram(formatar_resumo_diario(estatisticas))

    salvar_json(ARQUIVO_HISTORICO, historico)
    salvar_json(ARQUIVO_ESTATICAS, estatisticas)

    print(f"\n✅ Rodada finalizada • {total_posts} post(s)")

if __name__ == "__main__":
    main()
