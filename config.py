"""
⚙️ CONFIGURAÇÕES DO BOT
"""

import os

# ─────────────────────────────────────────
# 🔑 CREDENCIAIS
# ─────────────────────────────────────────
BOT_TOKEN   = os.getenv(
    "BOT_TOKEN",
    "8607746726:AAGhBBSN2vJ02r-G5MX1W QNOp3ZBzcM_U18"
)

CHANNEL_ID  = os.getenv(
    "CHANNEL_ID",
    "-1003874577875"
)

AFILIADO_ID = os.getenv(
    "AFILIADO_ID",
    "snakeshopping"
)

# ─────────────────────────────────────────
# 🔍 BUSCAS
# ─────────────────────────────────────────
BUSCAS = [

    # GERAIS
    {
        "q": "",
        "desconto_min": 40,
        "preco_min": 15,
        "preco_max": 300,
        "frete_gratis": True
    },

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

    # CATEGORIAS QUE MAIS CONVERTEM
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
]

# ─────────────────────────────────────────
# 🎯 FILTROS
# ─────────────────────────────────────────
FILTROS_GLOBAIS = {
    "avaliacao_min": 4.2,
    "vendidos_min": 20,
    "score_minimo": 58,
    "apenas_novo": True,
    "loja_oficial": False,
}

# ─────────────────────────────────────────
# 📊 SCORE
# ─────────────────────────────────────────
PESOS_SCORE = {
    "desconto": 35,
    "avaliacao": 25,
    "vendidos": 20,
    "frete_gratis": 15,
    "loja_oficial": 5,
}

# ─────────────────────────────────────────
# 🚫 BLACKLIST
# ─────────────────────────────────────────
BLACKLIST_TITULO = [

    "réplica",
    "replica",
    "similar",
    "genérico",
    "generico",
    "paralelo",
    "sem marca",
    "usado",
    "recondicionado",
    "display",
    "mostruario",
]

BLACKLIST_VENDEDOR = []

# ─────────────────────────────────────────
# 📤 POSTAGEM
# ─────────────────────────────────────────
PRODUTOS_POR_BUSCA = 2

# MUITO IMPORTANTE
PAUSA_ENTRE_POSTS_SEG = 25

POSTAR_RESUMO_DIARIO = True

# ─────────────────────────────────────────
# 🕒 HORÁRIOS
# ─────────────────────────────────────────
HORARIO_CATEGORIAS = {

    "manha": [
        "",
        "oferta",
        "smartwatch"
    ],

    "almoco": [
        "",
        "fone bluetooth"
    ],

    "tarde": [
        "",
        "caixa de som bluetooth"
    ],

    "noite": [
        "",
        "air fryer"
    ],

    "todas": None,
}
