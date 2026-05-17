"""
⚙️ CONFIGURAÇÕES DO BOT — edite aqui sem mexer no main.py
"""

# ─────────────────────────────────────────────────────────
# 🔑 CREDENCIAIS (use Secrets do GitHub, não edite aqui)
# ─────────────────────────────────────────────────────────
import os

# ⚠️  SEGURANÇA: Ao subir pro GitHub, use Secrets e deixe as strings vazias ""
# Para testar LOCAL, pode preencher aqui temporariamente
BOT_TOKEN   = os.getenv("BOT_TOKEN",   "8607746726:AAGhBBSN2vJ02r-G5MX1WQNOp3ZBzcM_U18")
CHANNEL_ID  = os.getenv("CHANNEL_ID",  "@SnakeShoppingOficial")
AFILIADO_ID = os.getenv("AFILIADO_ID", "snakeshopping")


# ─────────────────────────────────────────────────────────
# 🔍 CATEGORIAS E BUSCAS
# Cada busca pode ter seus próprios filtros individuais
# ─────────────────────────────────────────────────────────
BUSCAS = [
    # 💻 Tecnologia
    {"q": "notebook gamer",         "desconto_min": 15, "preco_min": 1500, "preco_max": 8000,  "frete_gratis": True},
    {"q": "smartphone samsung",     "desconto_min": 20, "preco_min": 800,  "preco_max": 5000,  "frete_gratis": True},
    {"q": "fone de ouvido bluetooth","desconto_min": 25, "preco_min": 50,  "preco_max": 1000,  "frete_gratis": False},
    {"q": "smart tv 50",            "desconto_min": 20, "preco_min": 1000, "preco_max": 6000,  "frete_gratis": True},
    {"q": "monitor gamer",          "desconto_min": 20, "preco_min": 600,  "preco_max": 4000,  "frete_gratis": True},
    {"q": "ssd nvme",               "desconto_min": 25, "preco_min": 80,   "preco_max": 800,   "frete_gratis": False},
    {"q": "tablet",                 "desconto_min": 20, "preco_min": 400,  "preco_max": 3000,  "frete_gratis": True},

    # 🏠 Casa e Cozinha
    {"q": "air fryer",              "desconto_min": 25, "preco_min": 100,  "preco_max": 1000,  "frete_gratis": True},
    {"q": "aspirador robô",         "desconto_min": 20, "preco_min": 200,  "preco_max": 2000,  "frete_gratis": True},
    {"q": "cafeteira expresso",     "desconto_min": 25, "preco_min": 100,  "preco_max": 1500,  "frete_gratis": False},

    # 💪 Esporte e Fitness
    {"q": "tênis esportivo",        "desconto_min": 30, "preco_min": 80,   "preco_max": 800,   "frete_gratis": True},
    {"q": "bicicleta elétrica",     "desconto_min": 15, "preco_min": 1000, "preco_max": 8000,  "frete_gratis": True},

    # 💄 Beleza e Saúde
    {"q": "perfume importado",      "desconto_min": 30, "preco_min": 80,   "preco_max": 1000,  "frete_gratis": False},
    {"q": "secador de cabelo",      "desconto_min": 25, "preco_min": 80,   "preco_max": 600,   "frete_gratis": False},
]


# ─────────────────────────────────────────────────────────
# 🧠 FILTROS GLOBAIS DE QUALIDADE
# Aplicados em TODOS os produtos independente da categoria
# ─────────────────────────────────────────────────────────
FILTROS_GLOBAIS = {
    "avaliacao_min":   4.0,    # Mínimo de estrelas (0 a 5)
    "vendidos_min":    10,     # Mínimo de unidades vendidas
    "score_minimo":    55,     # Score mínimo para postar (0 a 100)
    "apenas_novo":     True,   # True = só produtos novos (não usados)
    "loja_oficial":    False,  # True = só lojas oficiais (mais restritivo)
}


# ─────────────────────────────────────────────────────────
# ⚖️ PESOS DO SCORE INTELIGENTE (total deve = 100)
# Quanto maior o peso, mais esse fator influencia o ranking
# ─────────────────────────────────────────────────────────
PESOS_SCORE = {
    "desconto":      35,   # % de desconto
    "avaliacao":     25,   # Estrelas do produto
    "vendidos":      20,   # Quantidade de vendas
    "frete_gratis":  15,   # Tem frete grátis?
    "loja_oficial":   5,   # É loja oficial?
}


# ─────────────────────────────────────────────────────────
# 🚫 BLACKLIST — palavras que bloqueiam o produto
# Evita postar produtos de baixa qualidade ou suspeitos
# ─────────────────────────────────────────────────────────
BLACKLIST_TITULO = [
    "genérico", "réplica", "similar", "inspired",
    "paralelo", "sem marca", "kit 10", "kit 20",
]

BLACKLIST_VENDEDOR = []  # IDs de vendedores para bloquear (opcional)


# ─────────────────────────────────────────────────────────
# 📬 POSTAGEM
# ─────────────────────────────────────────────────────────
PRODUTOS_POR_BUSCA    = 2      # Máximo de produtos postados por categoria por rodada
PAUSA_ENTRE_POSTS_SEG = 4      # Segundos entre cada post (evita flood)
POSTAR_RESUMO_DIARIO  = True   # Posta um resumo às 21h com o total do dia


# ─────────────────────────────────────────────────────────
# ⏰ CATEGORIAS POR HORÁRIO
# Define quais categorias rodam em cada período do dia
# ─────────────────────────────────────────────────────────
HORARIO_CATEGORIAS = {
    "manha":  ["air fryer", "cafeteira expresso", "aspirador robô"],          # 8h
    "almoco": ["perfume importado", "tênis esportivo", "secador de cabelo"],   # 12h
    "tarde":  ["notebook gamer", "monitor gamer", "ssd nvme"],                 # 16h
    "noite":  ["smartphone samsung", "smart tv 50", "tablet"],                 # 19h
    "todas":  None,  # None = roda todas as categorias
}