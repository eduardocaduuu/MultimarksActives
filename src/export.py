"""
export.py - Funcoes de exportacao de dados.

Este modulo contem funcoes para exportar DataFrames
para formatos CSV e Excel.
"""

from io import BytesIO
from typing import Optional

import pandas as pd


def exportar_csv(df: pd.DataFrame) -> bytes:
    """
    Exporta um DataFrame para formato CSV.

    Args:
        df: DataFrame a ser exportado

    Returns:
        Bytes do arquivo CSV
    """
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


def exportar_excel(df: pd.DataFrame, nome_aba: str = "Dados") -> bytes:
    """
    Exporta um DataFrame para formato Excel (.xlsx).

    Args:
        df: DataFrame a ser exportado
        nome_aba: Nome da aba na planilha

    Returns:
        Bytes do arquivo Excel
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=nome_aba, index=False)

        # Ajustar largura das colunas automaticamente
        worksheet = writer.sheets[nome_aba]
        for idx, col in enumerate(df.columns):
            # Calcular largura baseada no conteudo
            if len(df) > 0:
                max_content = df[col].astype(str).map(len).max()
            else:
                max_content = 0

            max_length = max(max_content, len(str(col))) + 2

            # Limitar largura maxima e minima
            max_length = max(min(max_length, 50), 10)

            # Usar get_column_letter para suportar mais de 26 colunas
            col_letter = get_column_letter(idx + 1)
            worksheet.column_dimensions[col_letter].width = max_length

    return output.getvalue()


def exportar_multiplas_abas(
    dataframes: dict,
    formatacoes: Optional[dict] = None
) -> bytes:
    """
    Exporta multiplos DataFrames para um arquivo Excel com multiplas abas.

    Args:
        dataframes: Dicionario {nome_aba: DataFrame}
        formatacoes: Dicionario opcional com formatacoes por aba

    Returns:
        Bytes do arquivo Excel
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for nome_aba, df in dataframes.items():
            # Limitar nome da aba a 31 caracteres (limite do Excel)
            nome_aba_safe = nome_aba[:31]
            df.to_excel(writer, sheet_name=nome_aba_safe, index=False)

            # Ajustar largura das colunas
            worksheet = writer.sheets[nome_aba_safe]
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                    len(str(col))
                ) + 2
                max_length = min(max_length, 50)
                # Usar letras para colunas (A, B, C, ...)
                col_letter = get_column_letter(idx + 1)
                worksheet.column_dimensions[col_letter].width = max_length

    return output.getvalue()


def get_column_letter(col_idx: int) -> str:
    """
    Converte indice de coluna (1-based) para letra do Excel.

    Args:
        col_idx: Indice da coluna (1 = A, 2 = B, etc.)

    Returns:
        Letra(s) da coluna
    """
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def gerar_nome_arquivo(prefixo: str, extensao: str) -> str:
    """
    Gera nome de arquivo com timestamp.

    Args:
        prefixo: Prefixo do nome do arquivo
        extensao: Extensao do arquivo (sem ponto)

    Returns:
        Nome do arquivo formatado
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefixo}_{timestamp}.{extensao}"
