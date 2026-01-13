"""
transform.py - Funcoes de transformacao, merge e calculo de metricas.

Este modulo contem:
- Merge entre Vendas e BD Produtos
- Calculo de clientes ativos por ciclo
- Identificacao de clientes multimarcas
- Agregacoes e metricas principais
"""

from typing import Tuple, Dict, List, Any
import pandas as pd
import numpy as np

from .constants import (
    VENDAS_COL_SETOR,
    VENDAS_COL_NOME_REVENDEDORA,
    VENDAS_COL_CODIGO_REVENDEDORA,
    VENDAS_COL_CICLO,
    VENDAS_COL_CODIGO_PRODUTO,
    VENDAS_COL_NOME_PRODUTO,
    VENDAS_COL_TIPO,
    VENDAS_COL_QTD_ITENS,
    VENDAS_COL_VALOR,
    VENDAS_COL_MEIO_CAPTACAO,
    COL_CODIGO_PRODUTO_NORMALIZADO,
    COL_SKU_NORMALIZADO,
    COL_MARCA_BD,
    COL_NOME_BD,
    COL_MOTIVO_MATCH,
    COL_CLIENTE_ID,
    COL_MARCAS_DISTINTAS,
    COL_IS_MULTIMARCAS,
    COL_MARCAS_COMPRADAS,
    TIPO_VENDA,
    MARCA_DESCONHECIDA,
    MOTIVO_NAO_ENCONTRADO,
    ALERTA_SKU_NAO_ENCONTRADO_PERCENT,
)

from .io import criar_indice_sku, buscar_sku, gerar_id_cliente


def enriquecer_vendas_com_marca(
    df_vendas: pd.DataFrame,
    df_bd: pd.DataFrame,
    progress_callback=None
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Enriquece o DataFrame de vendas com informacoes de marca do BD Produtos.

    Args:
        df_vendas: DataFrame de vendas processado
        df_bd: DataFrame de BD Produtos processado
        progress_callback: Funcao opcional para reportar progresso (0.0 a 1.0)

    Returns:
        Tupla (DataFrame enriquecido, lista de avisos)
    """
    avisos = []

    # Criar indice de SKUs para busca rapida
    indice_sku = criar_indice_sku(df_bd)

    # Criar copia para nao modificar original
    df = df_vendas.copy()

    # Inicializar colunas
    df[COL_MARCA_BD] = None
    df[COL_NOME_BD] = None
    df[COL_MOTIVO_MATCH] = None

    # Processar cada linha (com progresso)
    total = len(df)
    resultados_marca = []
    resultados_nome = []
    resultados_motivo = []

    for idx, row in df.iterrows():
        codigo = row[COL_CODIGO_PRODUTO_NORMALIZADO]
        marca, nome, motivo = buscar_sku(codigo, indice_sku)

        resultados_marca.append(marca if marca else MARCA_DESCONHECIDA)
        resultados_nome.append(nome if nome else row[VENDAS_COL_NOME_PRODUTO])
        resultados_motivo.append(motivo)

        # Reportar progresso a cada 1000 linhas
        if progress_callback and idx % 1000 == 0:
            progress_callback(idx / total)

    df[COL_MARCA_BD] = resultados_marca
    df[COL_NOME_BD] = resultados_nome
    df[COL_MOTIVO_MATCH] = resultados_motivo

    # Gerar ID do cliente
    df[COL_CLIENTE_ID] = df.apply(gerar_id_cliente, axis=1)

    # Calcular estatisticas de match
    total_vendas = len(df[df[VENDAS_COL_TIPO] == TIPO_VENDA])
    nao_encontrados = len(df[
        (df[VENDAS_COL_TIPO] == TIPO_VENDA) &
        (df[COL_MOTIVO_MATCH] == MOTIVO_NAO_ENCONTRADO)
    ])

    if total_vendas > 0:
        percent_nao_encontrado = nao_encontrados / total_vendas

        avisos.append(
            f"SKUs encontrados: {total_vendas - nao_encontrados} / {total_vendas} "
            f"({(1 - percent_nao_encontrado) * 100:.1f}%)"
        )

        if percent_nao_encontrado > ALERTA_SKU_NAO_ENCONTRADO_PERCENT:
            avisos.append(
                f"ALERTA: {percent_nao_encontrado * 100:.1f}% dos SKUs nao foram "
                f"encontrados no BD Produtos. Verifique se a planilha BD esta completa."
            )

    # Contar matches por tipo
    match_exato = len(df[df[COL_MOTIVO_MATCH] == 'MATCH_EXATO'])
    match_zero = len(df[df[COL_MOTIVO_MATCH] == 'MATCH_COM_ZERO'])

    if match_zero > 0:
        avisos.append(
            f"{match_zero} SKUs encontrados por match com zero a esquerda"
        )

    if progress_callback:
        progress_callback(1.0)

    return df, avisos


def filtrar_vendas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra apenas registros do tipo 'Venda' para calculos.

    Args:
        df: DataFrame de vendas enriquecido

    Returns:
        DataFrame filtrado apenas com vendas
    """
    return df[df[VENDAS_COL_TIPO] == TIPO_VENDA].copy()


def calcular_metricas_cliente(df_vendas: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula metricas por cliente e ciclo.

    Identifica:
    - Clientes ativos (com ao menos 1 venda no ciclo)
    - Quantidade de marcas distintas por cliente/ciclo
    - Flag de multimarcas (2+ marcas)
    - Lista de marcas compradas

    Args:
        df_vendas: DataFrame de vendas filtrado (apenas Tipo=Venda)

    Returns:
        DataFrame com metricas por cliente/ciclo
    """
    # Agrupar por ciclo e cliente
    agg_cliente = df_vendas.groupby(
        [VENDAS_COL_CICLO, COL_CLIENTE_ID, VENDAS_COL_SETOR,
         VENDAS_COL_CODIGO_REVENDEDORA, VENDAS_COL_NOME_REVENDEDORA]
    ).agg({
        COL_MARCA_BD: lambda x: list(x.dropna().unique()),  # Lista de marcas unicas
        VENDAS_COL_QTD_ITENS: 'sum',
        VENDAS_COL_VALOR: 'sum'
    }).reset_index()

    # Renomear colunas
    agg_cliente.columns = [
        VENDAS_COL_CICLO, COL_CLIENTE_ID, VENDAS_COL_SETOR,
        VENDAS_COL_CODIGO_REVENDEDORA, VENDAS_COL_NOME_REVENDEDORA,
        COL_MARCAS_COMPRADAS, 'ItensTotal', 'ValorTotal'
    ]

    # Calcular quantidade de marcas distintas
    agg_cliente[COL_MARCAS_DISTINTAS] = agg_cliente[COL_MARCAS_COMPRADAS].apply(
        lambda x: len([m for m in x if m != MARCA_DESCONHECIDA])
    )

    # Flag de multimarcas (2+ marcas conhecidas)
    agg_cliente[COL_IS_MULTIMARCAS] = agg_cliente[COL_MARCAS_DISTINTAS] >= 2

    # Converter lista de marcas para string CSV
    agg_cliente[COL_MARCAS_COMPRADAS] = agg_cliente[COL_MARCAS_COMPRADAS].apply(
        lambda x: ', '.join(sorted([m for m in x if m != MARCA_DESCONHECIDA]))
    )

    return agg_cliente


def calcular_metricas_setor_ciclo(df_clientes: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega metricas por setor e ciclo.

    Args:
        df_clientes: DataFrame com metricas por cliente

    Returns:
        DataFrame com metricas agregadas por setor/ciclo
    """
    agg = df_clientes.groupby([VENDAS_COL_CICLO, VENDAS_COL_SETOR]).agg({
        COL_CLIENTE_ID: 'nunique',  # Clientes ativos
        COL_IS_MULTIMARCAS: 'sum',  # Clientes multimarcas
        'ItensTotal': 'sum',
        'ValorTotal': 'sum'
    }).reset_index()

    agg.columns = [
        VENDAS_COL_CICLO, VENDAS_COL_SETOR,
        'ClientesAtivos', 'ClientesMultimarcas',
        'ItensTotal', 'ValorTotal'
    ]

    # Calcular percentual de multimarcas
    agg['%Multimarcas'] = (
        agg['ClientesMultimarcas'] / agg['ClientesAtivos'] * 100
    ).round(1)

    return agg


def calcular_metricas_gerais(
    df_clientes: pd.DataFrame,
    df_vendas_filtrado: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calcula metricas gerais para exibicao em cards.

    Args:
        df_clientes: DataFrame com metricas por cliente
        df_vendas_filtrado: DataFrame de vendas filtrado (Tipo=Venda)

    Returns:
        Dicionario com metricas gerais
    """
    total_ativos = df_clientes[COL_CLIENTE_ID].nunique()
    total_multimarcas = df_clientes[df_clientes[COL_IS_MULTIMARCAS]][COL_CLIENTE_ID].nunique()

    percent_multimarcas = (total_multimarcas / total_ativos * 100) if total_ativos > 0 else 0

    total_itens = df_vendas_filtrado[VENDAS_COL_QTD_ITENS].sum()
    total_valor = df_vendas_filtrado[VENDAS_COL_VALOR].sum()

    return {
        'total_ativos': total_ativos,
        'total_multimarcas': total_multimarcas,
        'percent_multimarcas': percent_multimarcas,
        'total_itens': total_itens,
        'total_valor': total_valor
    }


def calcular_top_setores(
    df_setor_ciclo: pd.DataFrame,
    top_n: int = 5
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calcula top setores por valor e por clientes ativos.

    Args:
        df_setor_ciclo: DataFrame com metricas por setor/ciclo
        top_n: Quantidade de setores no ranking

    Returns:
        Tupla (top_por_valor, top_por_ativos)
    """
    # Agregar por setor (somando todos os ciclos)
    agg_setor = df_setor_ciclo.groupby(VENDAS_COL_SETOR).agg({
        'ClientesAtivos': 'sum',
        'ValorTotal': 'sum'
    }).reset_index()

    # Top por valor
    top_valor = agg_setor.nlargest(top_n, 'ValorTotal')[
        [VENDAS_COL_SETOR, 'ValorTotal']
    ].copy()

    # Top por clientes ativos
    top_ativos = agg_setor.nlargest(top_n, 'ClientesAtivos')[
        [VENDAS_COL_SETOR, 'ClientesAtivos']
    ].copy()

    return top_valor, top_ativos


def obter_detalhe_cliente(
    df_vendas_enriquecido: pd.DataFrame,
    cliente_id: str,
    ciclo: str = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Obtem detalhes de compras de um cliente especifico.

    Args:
        df_vendas_enriquecido: DataFrame de vendas com marcas
        cliente_id: ID do cliente (CodigoRevendedora ou fallback)
        ciclo: Ciclo especifico para filtrar (opcional)

    Returns:
        Tupla (DataFrame de itens, dicionario de resumo)
    """
    # Filtrar por cliente
    mask = df_vendas_enriquecido[COL_CLIENTE_ID] == cliente_id

    if ciclo:
        mask = mask & (df_vendas_enriquecido[VENDAS_COL_CICLO] == ciclo)

    df_cliente = df_vendas_enriquecido[mask].copy()

    # Filtrar apenas vendas para resumo
    df_vendas = df_cliente[df_cliente[VENDAS_COL_TIPO] == TIPO_VENDA]

    # Resumo
    resumo = {
        'marcas_distintas': df_vendas[COL_MARCA_BD].nunique(),
        'marcas_lista': sorted(df_vendas[COL_MARCA_BD].unique().tolist()),
        'total_itens': df_vendas[VENDAS_COL_QTD_ITENS].sum(),
        'total_valor': df_vendas[VENDAS_COL_VALOR].sum(),
        'ciclos': df_vendas[VENDAS_COL_CICLO].unique().tolist()
    }

    # Colunas para exibicao
    colunas_exibir = [
        VENDAS_COL_CICLO,
        VENDAS_COL_SETOR,
        VENDAS_COL_CODIGO_PRODUTO,
        VENDAS_COL_NOME_PRODUTO,
        COL_MARCA_BD,
        VENDAS_COL_QTD_ITENS,
        VENDAS_COL_VALOR,
        VENDAS_COL_MEIO_CAPTACAO,
        VENDAS_COL_TIPO
    ]

    colunas_disponiveis = [c for c in colunas_exibir if c in df_cliente.columns]

    return df_cliente[colunas_disponiveis], resumo


def gerar_auditoria_skus(df_vendas_enriquecido: pd.DataFrame) -> pd.DataFrame:
    """
    Gera tabela de auditoria para SKUs nao encontrados ou com match especial.

    Args:
        df_vendas_enriquecido: DataFrame de vendas com marcas

    Returns:
        DataFrame com linhas de auditoria
    """
    # Filtrar linhas com problemas ou match especial
    mask = (
        (df_vendas_enriquecido[COL_MOTIVO_MATCH] == MOTIVO_NAO_ENCONTRADO) |
        (df_vendas_enriquecido[COL_MOTIVO_MATCH] == 'MATCH_COM_ZERO')
    )

    df_audit = df_vendas_enriquecido[mask].copy()

    # Selecionar colunas relevantes
    colunas = [
        VENDAS_COL_CICLO,
        VENDAS_COL_SETOR,
        VENDAS_COL_CODIGO_REVENDEDORA,
        VENDAS_COL_CODIGO_PRODUTO,
        COL_CODIGO_PRODUTO_NORMALIZADO,
        VENDAS_COL_NOME_PRODUTO,
        COL_MOTIVO_MATCH
    ]

    df_result = df_audit[colunas].drop_duplicates()

    # Renomear coluna de motivo
    df_result = df_result.rename(columns={
        COL_CODIGO_PRODUTO_NORMALIZADO: 'CodigoProduto_normalizado',
        COL_MOTIVO_MATCH: 'Motivo'
    })

    return df_result


def aplicar_filtros(
    df: pd.DataFrame,
    ciclos: List[str] = None,
    setores: List[str] = None,
    marcas: List[str] = None,
    apenas_multimarcas: bool = False
) -> pd.DataFrame:
    """
    Aplica filtros ao DataFrame.

    Args:
        df: DataFrame a ser filtrado
        ciclos: Lista de ciclos para filtrar
        setores: Lista de setores para filtrar
        marcas: Lista de marcas para filtrar
        apenas_multimarcas: Se True, filtra apenas clientes multimarcas

    Returns:
        DataFrame filtrado
    """
    df_filtrado = df.copy()

    if ciclos and len(ciclos) > 0:
        df_filtrado = df_filtrado[df_filtrado[VENDAS_COL_CICLO].isin(ciclos)]

    if setores and len(setores) > 0:
        df_filtrado = df_filtrado[df_filtrado[VENDAS_COL_SETOR].isin(setores)]

    if marcas and len(marcas) > 0 and COL_MARCA_BD in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_MARCA_BD].isin(marcas)]

    if apenas_multimarcas and COL_IS_MULTIMARCAS in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_IS_MULTIMARCAS] == True]

    return df_filtrado
