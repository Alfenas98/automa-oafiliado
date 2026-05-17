"""
⚙️ CONFIGURAÇÕES DO BOT — edite aqui sem mexer no main.py
"""

import os

# ─────────────────────────────────────────────────────────
# 🔑 CREDENCIAIS
# ─────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN",   "8607746726:AAGhBBSN2vJ02r-G5MX1WQNOp3ZBzcM_U18")
CHANNEL_ID  = os.getenv("CHANNEL_ID",  "@SnakeShoppingOficial")
AFILIADO_ID = os.getenv("AFILIADO_ID", "snakeshopping")

# ─────────────────────────────────────────────────────────
# 🔍 CATEGORIAS E BUSCAS
# ─────────────────────────────────────────────────────────
BUSCAS = [
    # 🔥 BUSCA GERAL - QUALQUER PRODUTO EM OFERTA ATÉ R$300 (PRIORIDADE ALTA)
    {"q": "",               "desconto_min": 35, "preco_min": 15,  "preco_max": 300,  "frete_gratis": True},
    {"q": "promocao",       "desconto_min": 35, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    {"q": "oferta",         "desconto_min": 35, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    {"q": "desconto",       "desconto_min": 30, "preco_min": 15,  "preco_max": 300,  "frete_gratis": True},

    # 💻 Tecnologia (mantidas, mas só as mais relevantes)
    {"q": "notebook gamer", "desconto_min": 15, "preco_min": 1500, "preco_max": 8000, "frete_gratis": True},
    {"q": "monitor gamer",  "desconto_min": 20, "preco_min": 600,  "preco_max": 4000, "frete_gratis": True},
    {"q": "ssd nvme",       "desconto_min": 25, "preco_min": 80,   "preco_max": 800,  "frete_gratis": False},
    {"q": "fone de ouvido bluetooth", "desconto_min": 25, "preco_min": 50, "preco_max": 600, "frete_gratis": True},

    # 🏠 Casa e Cozinha
    {"q": "air fryer",      "desconto_min": 25, "preco_min": 100, "preco_max": 1000, "frete_gratis": True},
    {"q": "aspirador robô", "desconto_min": 20, "preco_min": 200, "preco_max": 2000, "frete_gratis": True},

    # Outras categorias (pode descomentar se quiser)
    # {"q": "smartphone samsung", "desconto_min": 20, "preco_min": 800, "preco_max": 5000, "frete_gratis": True},
]

# ─────────────────────────────────────────────────────────
# 🧠 FILTROS GLOBAIS DE QUALIDADE
# ─────────────────────────────────────────────────────────
FILTROS_GLOBAIS = {
    "avaliacao_min": 4.0,
    "vendidos_min": 10,
    "score_minimo": 58,      # Aumentei um pouco por causa da busca geral
    "apenas_novo": True,
    "loja_oficial": False,
}

# ─────────────────────────────────────────────────────────
# ⚖️ PESOS DO SCORE
# ─────────────────────────────────────────────────────────
PESOS_SCORE = {
    "desconto": 35,
    "avaliacao": 25,
    "vendidos": 20,
    "frete_gratis": 15,
    "loja_oficial": 5,
}

# ─────────────────────────────────────────────────────────
# 🚫 BLACKLIST
# ─────────────────────────────────────────────────────────
BLACKLIST_TITULO = [
    "genérico", "réplica", "similar", "inspired",
    "paralelo", "sem marca", "kit 10", "kit 20", "usado"
]

BLACKLIST_VENDEDOR = []

# ─────────────────────────────────────────────────────────
# 📬 POSTAGEM
# ─────────────────────────────────────────────────────────
PRODUTOS_POR_BUSCA    = 3     # Aumentei um pouco para a busca geral
PAUSA_ENTRE_POSTS_SEG = 4
POSTAR_RESUMO_DIARIO  = True

# ─────────────────────────────────────────────────────────
# ⏰ CATEGORIAS POR HORÁRIO (atualizado)
# ─────────────────────────────────────────────────────────
HORARIO_CATEGORIAS = {
    "manha":  ["air fryer", "aspirador robô"], 
    "almoco": ["promocao", "oferta"],           # Busca geral
    "tarde":  ["notebook gamer", "monitor gamer", "ssd nvme"],
    "noite":  ["", "promocao", "oferta"],       # Busca geral
    "todas":  None,
}
