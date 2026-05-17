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
# 🔍 BUSCAS - AGORA FOCADO EM QUALQUER PRODUTO ATÉ R$300
# ─────────────────────────────────────────────────────────
BUSCAS = [
    # 🔥 BUSCA GERAL (principal)
    {"q": "",               "desconto_min": 35, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    {"q": "promocao",       "desconto_min": 35, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    {"q": "oferta",         "desconto_min": 35, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    {"q": "desconto",       "desconto_min": 30, "preco_min": 10,  "preco_max": 300,  "frete_gratis": True},
    
    # Algumas categorias específicas (opcional - você pode remover depois)
    {"q": "air fryer",      "desconto_min": 25, "preco_min": 100, "preco_max": 800,  "frete_gratis": True},
    {"q": "fone de ouvido", "desconto_min": 30, "preco_min": 30,  "preco_max": 300,  "frete_gratis": True},
]

# ─────────────────────────────────────────────────────────
# FILTROS GLOBAIS
# ─────────────────────────────────────────────────────────
FILTROS_GLOBAIS = {
    "avaliacao_min": 4.0,
    "vendidos_min": 8,
    "score_minimo": 55,
    "apenas_novo": True,
    "loja_oficial": False,
}

# PESOS DO SCORE
PESOS_SCORE = {
    "desconto": 35,
    "avaliacao": 25,
    "vendidos": 20,
    "frete_gratis": 15,
    "loja_oficial": 5,
}

# BLACKLIST
BLACKLIST_TITULO = [
    "genérico", "réplica", "similar", "inspired", "paralelo", 
    "sem marca", "kit 10", "kit 20", "usado", "recondicionado"
]

BLACKLIST_VENDEDOR = []

# POSTAGEM
PRODUTOS_POR_BUSCA    = 3
PAUSA_ENTRE_POSTS_SEG = 4
POSTAR_RESUMO_DIARIO  = True

# HORÁRIO (agora prioriza busca geral)
HORARIO_CATEGORIAS = {
    "manha":  ["", "promocao", "oferta"],
    "almoco": ["", "promocao", "oferta"],
    "tarde":  ["", "promocao", "oferta"],
    "noite":  ["", "promocao", "oferta"],
    "todas":  None,
}
