"""
🤖 Bot de Afiliados ML — Versão Inteligente (2026)
Usando Web Scraping com Playwright
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
    
    vendidos = produto.get("vendidos", 0) or 0
    import math
    s_vendidos = (math.log10(max(vendidos, 1)) / 4) * p["vendidos"]
    
    s_frete = p["frete_gratis"] if produto.get("frete_gratis") else 0
    s_loja = p["loja_oficial"] if produto.get("loja_oficial") else 0
    
    total = s_desconto + s_avaliacao + s_vendidos + s_frete + s_loja
    return round(total, 1)

# ====================== SCRAPING ======================
def buscar_ml(busca: dict, limite: int = 20) -> list:
    query = busca["q"].replace(" ", "-").lower()
    url = f"https://lista.mercadolivre.com.br/{query}"

    # Filtros na URL
    if busca.get("preco_min") or busca.get("preco_max"):
        url += f"_PriceRange_{busca.get('preco_min',0)}-{busca.get('preco_max','*')}"
    if busca.get("frete_gratis"):
        url += "_FreightCost_0"

    print(f" 🌐 Scraping → {url}")

    produtos = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)  # Aguarda carregamento dinâmico

            soup = BeautifulSoup(page.content(), "lxml")

            # Seletores atualizados (2026)
            cards = soup.select("div.andes-card, div.ui-search-result__wrapper, article.andes-card")
            
            for card in cards[:limite]:
                try:
                    # Título
                    titulo_tag = card.select_one("h2.ui-search-item__title, h3.poly-component__title, a.ui-search-link")
                    titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""

                    # Preços
                    preco_atual_tag = card.select_one("span.andes-money-amount__fraction")
                    preco_original_tag = card.select_one("s span.andes-money-amount__fraction, span.andes-money-amount--previous .andes-money-amount__fraction")

                    if not preco_atual_tag or not titulo:
                        continue

                    def limpar_preco(tag):
                        if not tag:
                            return 0
                        text = tag.get_text(strip=True).replace(".", "").replace(",", ".")
                        return float(text) if text.replace(".", "").isdigit() else 0

                    preco_atual = limpar_preco(preco_atual_tag)
                    preco_original = limpar_preco(preco_original_tag) or preco_atual

                    if preco_original <= preco_atual * 1.05:  # pelo menos ~5% de desconto
                        continue

                    desconto = int(((preco_original - preco_atual) / preco_original) * 100)
                    if desconto < busca.get("desconto_min", 15):
                        continue

                    # Link
                    link_tag = card.select_one("a.ui-search-link, a.poly-component__title-link")
                    link = "https://www.mercadolivre.com.br" + link_tag["href"] if link_tag and link_tag.get("href") else ""

                    # Imagem
                    img = card.select_one("img.ui-search-result-image__image, img.andes-image__element")
                    thumbnail = img.get("src") or img.get("data-src", "") if img else ""

                    produto = {
                        "id": link.split("/")[-1].split("-")[0] if link else str(hash(titulo)),
                        "titulo": titulo,
                        "preco_original": preco_original,
                        "preco_atual": preco_atual,
                        "desconto": desconto,
                        "avaliacao": 4.5,  # placeholder (melhorar depois)
                        "qtd_avaliacoes": 100,
                        "vendidos": 500,   # placeholder
                        "frete_gratis": "frete grátis" in card.get_text().lower() or busca.get("frete_gratis", False),
                        "loja_oficial": "oficial" in card.get_text().lower(),
                        "thumbnail": thumbnail.replace("http://", "https://"),
                        "url": link,
                        "vendedor": "",
                        "categoria": busca["q"],
                    }
                    produtos.append(produto)

                except:
                    continue

            browser.close()

    except Exception as e:
        print(f" ❌ Erro grave no scraping: {e}")

    print(f" ✅ {len(produtos)} produtos encontrados via scraping")
    return produtos

# ====================== RESTO DO CÓDIGO (mantido igual) ======================
# ... (aplicar_filtros_inteligentes, gerar_link_afiliado, formatar_mensagem, etc.)

# Cole o resto das suas funções aqui (não mudei elas, só a busca)

def aplicar_filtros_inteligentes(produtos: list) -> list:
    f = cfg.FILTROS_GLOBAIS
    filtrados = []
    for p in produtos:
        titulo_lower = p["titulo"].lower()
        if any(bl in titulo_lower for bl in cfg.BLACKLIST_TITULO):
            continue
        if str(p["vendedor"]) in cfg.BLACKLIST_VENDEDOR:
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

# ... (mantenha todas as outras funções: gerar_link_afiliado, formatar_*, enviar_telegram, buscas_do_horario, main())

# ====================== MAIN ======================
if __name__ == "__main__":
    main()
