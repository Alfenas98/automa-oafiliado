"""
⚙️ CONFIGURAÇÕES DO BOT
"""

import os

# ─────────────────────────────────────────
# 🔑 CREDENCIAIS TELEGRAM
# ─────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN",   "8607746726:AAGhBBSN2vJ02r-G5MX1WQNOp3ZBzcM_U18")
CHANNEL_ID  = os.getenv("CHANNEL_ID",  "-1003874577875")
AFILIADO_ID = os.getenv("AFILIADO_ID", "snakeshopping")

# ─────────────────────────────────────────
# 🔑 CREDENCIAIS MERCADO LIVRE
# ─────────────────────────────────────────
ML_CLIENT_ID     = os.getenv("ML_CLIENT_ID",     "2889407230135324")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET",  "7bOwf2tqeh9YLe2iRODIs8fwFBEoPYdF")
ML_ACCESS_TOKEN  = os.getenv("ML_ACCESS_TOKEN",   "APP_USR-2889407230135324-051721-f71d3b79670bc13f90fd2adb83e32df1-442174426")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN",  "TG-6a0a676383a4c80001b23287-442174426")

# ─────────────────────────────────────────
# 🔍 BUSCAS
# ─────────────────────────────────────────
BUSCAS = [
    {
        "q": "oferta",
        "desconto_min": 35,
        "preco_min": 15,
        "preco_max": 300,
        "frete_gratis": True
    },
    {
        "q": "promocao",
        "desconto_min": 35,
        "preco_min": 15,
        "preco_max": 300,
        "frete_gratis": True
    },
    {
        "q": "fone bluetooth",
        "desconto_min": 30,
        "preco_min": 25,
        "preco_max": 250,
        "frete_gratis": True
    },
    {
        "q": "smartwatch",
        "desconto_min": 30,
        "preco_min": 40,
        "preco_max": 300,
        "frete_gratis": True
    },
    {
        "q": "air fryer",
        "desconto_min": 25,
        "preco_min": 120,
        "preco_max": 900,
        "frete_gratis": True
    },
    {
        "q": "caixa de som bluetooth",
        "desconto_min": 30,
        "preco_min": 40,
        "preco_max": 300,
        "frete_gratis": True
    },
    {
        "q": "notebook",
        "desconto_min": 15,
        "preco_min": 1500,
        "preco_max": 6000,
        "frete_gratis": True
    },
    {
        "q": "smartphone",
        "desconto_min": 20,
        "preco_min": 500,
        "preco_max": 4000,
        "frete_gratis": True
    },
]

# ─────────────────────────────────────────
# 🎯 FILTROS GLOBAIS
# ─────────────────────────────────────────
FILTROS_GLOBAIS = {
    "avaliacao_min": 4.0,
    "vendidos_min":  10,
    "score_minimo":  50,
    "apenas_novo":   True,
    "loja_oficial":  False,
}

# ─────────────────────────────────────────
# 📊 PESOS DO SCORE
# ─────────────────────────────────────────
PESOS_SCORE = {
    "desconto":     35,
    "avaliacao":    25,
    "vendidos":     20,
    "frete_gratis": 15,
    "loja_oficial":  5,
}

# ─────────────────────────────────────────
# 🚫 BLACKLIST
# ─────────────────────────────────────────
BLACKLIST_TITULO = [
    "réplica", "replica", "similar", "genérico", "generico",
    "paralelo", "sem marca", "usado", "recondicionado",
    "display", "mostruario",
]

BLACKLIST_VENDEDOR = []

# ─────────────────────────────────────────
# 📤 POSTAGEM
# ─────────────────────────────────────────
PRODUTOS_POR_BUSCA    = 2
PAUSA_ENTRE_POSTS_SEG = 25
POSTAR_RESUMO_DIARIO  = True

# ─────────────────────────────────────────
# 🕒 CATEGORIAS POR HORÁRIO
# ─────────────────────────────────────────
HORARIO_CATEGORIAS = {
    "manha":  ["oferta", "smartwatch", "fone bluetooth"],
    "almoco": ["oferta", "caixa de som bluetooth"],
    "tarde":  ["oferta", "notebook", "smartphone"],
    "noite":  ["oferta", "air fryer"],
    "todas":  None,
}
