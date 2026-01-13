"""
constants.py - Constantes e configuracoes do projeto Multimarks Active Circles.

Define nomes de colunas padronizados, marcas esperadas e configuracoes gerais
para garantir consistencia em todo o projeto.
"""

# =============================================================================
# COLUNAS DO BD PRODUTOS (planilha de cadastro de produtos)
# =============================================================================
BD_COL_SKU = "SKU"
BD_COL_NOME = "Nome"
BD_COL_MARCA = "Marca"

BD_REQUIRED_COLUMNS = [BD_COL_SKU, BD_COL_NOME, BD_COL_MARCA]

# =============================================================================
# COLUNAS DA PLANILHA DE VENDAS
# =============================================================================
VENDAS_COL_SETOR = "Setor"
VENDAS_COL_NOME_REVENDEDORA = "NomeRevendedora"
VENDAS_COL_CODIGO_REVENDEDORA = "CodigoRevendedora"
VENDAS_COL_CICLO = "CicloFaturamento"
VENDAS_COL_CODIGO_PRODUTO = "CodigoProduto"
VENDAS_COL_NOME_PRODUTO = "NomeProduto"
VENDAS_COL_TIPO = "Tipo"
VENDAS_COL_QTD_ITENS = "QuantidadeItens"
VENDAS_COL_VALOR = "ValorPraticado"
VENDAS_COL_MEIO_CAPTACAO = "MeioCaptacao"

VENDAS_REQUIRED_COLUMNS = [
    VENDAS_COL_SETOR,
    VENDAS_COL_NOME_REVENDEDORA,
    VENDAS_COL_CODIGO_REVENDEDORA,
    VENDAS_COL_CICLO,
    VENDAS_COL_CODIGO_PRODUTO,
    VENDAS_COL_NOME_PRODUTO,
    VENDAS_COL_TIPO,
    VENDAS_COL_QTD_ITENS,
    VENDAS_COL_VALOR,
]

# Coluna opcional de vendas
VENDAS_OPTIONAL_COLUMNS = [VENDAS_COL_MEIO_CAPTACAO]

# =============================================================================
# MARCAS ESPERADAS DO GRUPO
# =============================================================================
MARCAS_GRUPO = [
    "oBoticário",
    "Eudora",
    "AuAmigos",
    "Quem Disse Berenice",
    "QDB",  # Alias para Quem Disse Berenice
    "O.U.I",
]

# Mapeamento de aliases para nome padronizado (para normalizar variações)
MARCA_ALIASES = {
    "QDB": "Quem Disse Berenice",
    "QUEM DISSE BERENICE": "Quem Disse Berenice",
    "OBOTICARIO": "oBoticário",
    "O BOTICARIO": "oBoticário",
    "BOTICARIO": "oBoticário",
    "EUDORA": "Eudora",
    "AUAMIGOS": "AuAmigos",
    "AU AMIGOS": "AuAmigos",
    "OUI": "O.U.I",
    "O.U.I": "O.U.I",
}

# =============================================================================
# VALORES ESPECIAIS E FLAGS
# =============================================================================
TIPO_VENDA = "Venda"  # Valor que indica uma venda válida
MARCA_DESCONHECIDA = "DESCONHECIDA"  # Quando SKU não é encontrado no BD
SKU_NAO_ENCONTRADO = "SKU_NAO_ENCONTRADO"

# Motivos de auditoria para SKUs
MOTIVO_NAO_ENCONTRADO = "NAO_ENCONTRADO"
MOTIVO_MATCH_COM_ZERO = "MATCH_COM_ZERO"
MOTIVO_MATCH_EXATO = "MATCH_EXATO"

# =============================================================================
# CONFIGURACOES DE PROCESSAMENTO
# =============================================================================
# Percentual de SKUs não encontrados que gera alerta (5%)
ALERTA_SKU_NAO_ENCONTRADO_PERCENT = 0.05

# Tamanho mínimo/máximo esperado para SKU/CodigoProduto
SKU_MIN_DIGITOS = 4
SKU_MAX_DIGITOS = 5

# =============================================================================
# COLUNAS INTERNAS (criadas durante processamento)
# =============================================================================
COL_SKU_NORMALIZADO = "SKU_normalizado"
COL_CODIGO_PRODUTO_NORMALIZADO = "CodigoProduto_normalizado"
COL_MARCA_BD = "Marca_BD"  # Marca vinda do BD após merge
COL_NOME_BD = "Nome_BD"    # Nome do produto vindo do BD após merge
COL_MOTIVO_MATCH = "Motivo_Match"
COL_CLIENTE_ID = "ClienteID"  # Identificador único do cliente
COL_MARCAS_DISTINTAS = "QtdeMarcasDistintas"
COL_IS_MULTIMARCAS = "IsMultimarcas"
COL_MARCAS_COMPRADAS = "MarcasCompradas"

# =============================================================================
# TEXTOS DA INTERFACE
# =============================================================================
APP_TITLE = "Multimarks Active Circles"
APP_SUBTITLE = "Analise de Revendedores Ativos e Multimarcas por Ciclo"
APP_ICON = ":chart_with_upwards_trend:"

TAB_VISAO_GERAL = "Visao Geral"
TAB_MULTIMARCAS = "Multimarcas"
TAB_AUDITORIA = "Auditoria"
TAB_CLIENTE = "Detalhe Cliente"

# =============================================================================
# FORMATACAO
# =============================================================================
FORMATO_MOEDA = "R$ {:,.2f}"
FORMATO_PERCENTUAL = "{:.1f}%"
FORMATO_NUMERO = "{:,.0f}"
