"""
reports.py - Funcoes para geracao de tabelas e relatorios agregados.

Este modulo contem funcoes para formatar e preparar dados
para exibicao na interface do usuario.
"""

from typing import Dict, List, Any
import pandas as pd
import math

from .transform import arredondar_percentual
from .constants import (
    VENDAS_COL_CICLO,
    VENDAS_COL_SETOR,
    VENDAS_COL_CODIGO_REVENDEDORA,
    VENDAS_COL_NOME_REVENDEDORA,
    COL_CLIENTE_ID,
    COL_MARCAS_DISTINTAS,
    COL_IS_MULTIMARCAS,
    COL_MARCAS_COMPRADAS,
    FORMATO_MOEDA,
    FORMATO_PERCENTUAL,
    FORMATO_NUMERO,
)


def formatar_tabela_setor_ciclo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de ativos por setor e ciclo para exibicao.

    Args:
        df: DataFrame com metricas por setor/ciclo

    Returns:
        DataFrame formatado para exibicao
    """
    df_fmt = df.copy()

    # Zerar setor "INICIOS CENTRAL 13706" apenas na visualizacao (calculos permanecem)
    SETOR_ZERAR_VISUALIZACAO = "INICIOS CENTRAL 13706"
    mask_setor = df_fmt[VENDAS_COL_SETOR] == SETOR_ZERAR_VISUALIZACAO
    if mask_setor.any():
        df_fmt.loc[mask_setor, 'ClientesAtivos'] = 0
        df_fmt.loc[mask_setor, 'ClientesMultimarcas'] = 0
        df_fmt.loc[mask_setor, '%Multimarcas'] = 0
        df_fmt.loc[mask_setor, 'ItensTotal'] = 0
        df_fmt.loc[mask_setor, 'ValorTotal'] = 0

    # Renomear colunas para exibicao
    colunas_renomear = {
        VENDAS_COL_CICLO: 'Ciclo',
        VENDAS_COL_SETOR: 'Setor',
        'ClientesAtivos': 'Clientes Ativos',
        'ClientesMultimarcas': 'Multimarcas',
        '%Multimarcas': '% Multimarcas',
        'ItensTotal': 'Total Itens',
        'ValorTotal': 'Valor Total'
    }

    df_fmt = df_fmt.rename(columns=colunas_renomear)

    # Ordenar por ciclo e setor
    if 'Ciclo' in df_fmt.columns:
        df_fmt = df_fmt.sort_values(['Ciclo', 'Setor'])

    return df_fmt


def formatar_tabela_multimarcas(df_clientes: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de clientes multimarcas para exibicao.

    Args:
        df_clientes: DataFrame com metricas por cliente

    Returns:
        DataFrame formatado apenas com multimarcas
    """
    # Filtrar apenas multimarcas
    df_multi = df_clientes[df_clientes[COL_IS_MULTIMARCAS] == True].copy()

    # Selecionar e ordenar colunas
    colunas = [
        VENDAS_COL_CICLO,
        VENDAS_COL_SETOR,
        VENDAS_COL_CODIGO_REVENDEDORA,
        VENDAS_COL_NOME_REVENDEDORA,
        COL_MARCAS_DISTINTAS,
        COL_MARCAS_COMPRADAS,
        'ItensTotal',
        'ValorTotal'
    ]

    colunas_disponiveis = [c for c in colunas if c in df_multi.columns]
    df_fmt = df_multi[colunas_disponiveis].copy()

    # Renomear colunas
    colunas_renomear = {
        VENDAS_COL_CICLO: 'Ciclo',
        VENDAS_COL_SETOR: 'Setor',
        VENDAS_COL_CODIGO_REVENDEDORA: 'Codigo',
        VENDAS_COL_NOME_REVENDEDORA: 'Nome',
        COL_MARCAS_DISTINTAS: 'Qtde Marcas',
        COL_MARCAS_COMPRADAS: 'Marcas',
        'ItensTotal': 'Total Itens',
        'ValorTotal': 'Valor Total'
    }

    df_fmt = df_fmt.rename(columns=colunas_renomear)

    # Ordenar
    if 'Ciclo' in df_fmt.columns:
        df_fmt = df_fmt.sort_values(['Ciclo', 'Valor Total'], ascending=[True, False])

    return df_fmt


def formatar_tabela_auditoria(df_audit: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de auditoria de SKUs para exibicao.

    Args:
        df_audit: DataFrame de auditoria

    Returns:
        DataFrame formatado
    """
    df_fmt = df_audit.copy()

    # Renomear colunas
    colunas_renomear = {
        VENDAS_COL_CICLO: 'Ciclo',
        VENDAS_COL_SETOR: 'Setor',
        VENDAS_COL_CODIGO_REVENDEDORA: 'Cod. Revendedora',
        'CodigoProduto': 'Cod. Produto (Original)',
        'CodigoProduto_normalizado': 'Cod. Produto (Normalizado)',
        'NomeProduto': 'Nome Produto',
        'Motivo': 'Motivo'
    }

    df_fmt = df_fmt.rename(columns=colunas_renomear)

    return df_fmt


def gerar_resumo_metricas(metricas: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Gera lista de metricas formatadas para exibicao em cards.

    Args:
        metricas: Dicionario com metricas gerais

    Returns:
        Lista de dicionarios com label, valor e formato
    """
    return [
        {
            'label': 'Clientes Ativos',
            'valor': metricas['total_ativos'],
            'formato': 'numero',
            'icone': ':busts_in_silhouette:'
        },
        {
            'label': 'Multimarcas',
            'valor': metricas['total_multimarcas'],
            'formato': 'numero',
            'icone': ':star:'
        },
        {
            'label': '% Multimarcas',
            'valor': metricas['percent_multimarcas'],
            'formato': 'percentual',
            'icone': ':chart_with_upwards_trend:'
        },
        {
            'label': 'Total de Itens',
            'valor': metricas['total_itens'],
            'formato': 'numero',
            'icone': ':package:'
        },
        {
            'label': 'Valor Total',
            'valor': metricas['total_valor'],
            'formato': 'moeda',
            'icone': ':moneybag:'
        }
    ]


def formatar_valor(valor: Any, formato: str) -> str:
    """
    Formata um valor de acordo com o tipo especificado.

    Args:
        valor: Valor a ser formatado
        formato: Tipo de formato ('numero', 'moeda', 'percentual')

    Returns:
        String formatada
    """
    if pd.isna(valor):
        return "-"

    if formato == 'moeda':
        return FORMATO_MOEDA.format(valor)
    elif formato == 'percentual':
        return FORMATO_PERCENTUAL.format(valor)
    elif formato == 'numero':
        return FORMATO_NUMERO.format(valor)
    else:
        return str(valor)


def gerar_lista_clientes_para_selecao(df_clientes: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Gera lista de clientes para dropdown de selecao.

    Args:
        df_clientes: DataFrame com metricas por cliente

    Returns:
        Lista de dicionarios com id e label para cada cliente
    """
    clientes = df_clientes[[
        COL_CLIENTE_ID,
        VENDAS_COL_CODIGO_REVENDEDORA,
        VENDAS_COL_NOME_REVENDEDORA,
        VENDAS_COL_SETOR
    ]].drop_duplicates()

    resultado = []
    for _, row in clientes.iterrows():
        codigo = row[VENDAS_COL_CODIGO_REVENDEDORA]
        nome = row[VENDAS_COL_NOME_REVENDEDORA]
        setor = row[VENDAS_COL_SETOR]

        # Label para exibicao
        if pd.notna(codigo) and str(codigo).strip():
            label = f"{codigo} - {nome} ({setor})"
        else:
            label = f"{nome} ({setor})"

        resultado.append({
            'id': row[COL_CLIENTE_ID],
            'label': label,
            'codigo': str(codigo) if pd.notna(codigo) else '',
            'nome': str(nome),
            'setor': str(setor)
        })

    # Ordenar por label
    resultado.sort(key=lambda x: x['label'])

    return resultado


def calcular_estatisticas_ciclo(df_setor_ciclo: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula estatisticas totais por ciclo.

    Args:
        df_setor_ciclo: DataFrame com metricas por setor/ciclo

    Returns:
        DataFrame com totais por ciclo
    """
    agg = df_setor_ciclo.groupby(VENDAS_COL_CICLO).agg({
        'ClientesAtivos': 'sum',
        'ClientesMultimarcas': 'sum',
        'ItensTotal': 'sum',
        'ValorTotal': 'sum'
    }).reset_index()

    # Calcular percentual
    agg['%Multimarcas'] = agg.apply(
        lambda row: arredondar_percentual(
            (row['ClientesMultimarcas'] / row['ClientesAtivos'] * 100) if row['ClientesAtivos'] > 0 else 0
        ),
        axis=1
    )

    # Ordenar por ciclo
    agg = agg.sort_values(VENDAS_COL_CICLO)

    # Formatar valores
    agg['ItensTotal'] = agg['ItensTotal'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
    agg['ValorTotal'] = agg['ValorTotal'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    # Renomear
    agg = agg.rename(columns={
        VENDAS_COL_CICLO: 'Ciclo',
        'ClientesAtivos': 'Clientes Ativos',
        'ClientesMultimarcas': 'Multimarcas',
        '%Multimarcas': '% Multimarcas',
        'ItensTotal': 'Total Itens',
        'ValorTotal': 'Valor Total'
    })

    return agg
