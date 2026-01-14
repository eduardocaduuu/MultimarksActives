"""
io.py - Funcoes de leitura, validacao e normalizacao de dados.

Este modulo contem:
- Leitura de arquivos Excel/CSV
- Validacao de colunas obrigatorias
- Normalizacao de SKU/CodigoProduto (preservando zeros a esquerda)
- Estrategia de match robusto para SKUs de 4/5 digitos
"""

import re
import csv
from typing import Tuple, List, Optional, Set
from io import BytesIO

import pandas as pd

from .constants import (
    BD_REQUIRED_COLUMNS,
    BD_COL_SKU,
    BD_COL_NOME,
    BD_COL_MARCA,
    VENDAS_REQUIRED_COLUMNS,
    VENDAS_OPTIONAL_COLUMNS,
    VENDAS_COL_CODIGO_PRODUTO,
    VENDAS_COL_TIPO,
    TIPO_VENDA,
    COL_SKU_NORMALIZADO,
    COL_CODIGO_PRODUTO_NORMALIZADO,
    MARCAS_GRUPO,
    MARCA_ALIASES,
    SKU_MIN_DIGITOS,
    SKU_MAX_DIGITOS,
)


class DataValidationError(Exception):
    """Excecao customizada para erros de validacao de dados."""
    pass


def normalizar_sku(valor: any) -> str:
    """
    Normaliza um valor de SKU/CodigoProduto.

    Regras:
    1. Converter para string
    2. Remover espacos em branco
    3. Remover caracteres nao numericos
    4. Preservar zeros a esquerda (nao converter para int)

    Args:
        valor: Valor a ser normalizado (pode ser str, int, float, etc.)

    Returns:
        String normalizada do SKU
    """
    if pd.isna(valor):
        return ""

    # Converter para string
    valor_str = str(valor)

    # Remover espacos
    valor_str = valor_str.strip()

    # Remover caracteres nao numericos (manter apenas digitos)
    valor_str = re.sub(r'[^\d]', '', valor_str)

    return valor_str


def normalizar_marca(marca: str) -> str:
    """
    Normaliza o nome da marca aplicando aliases conhecidos.

    Args:
        marca: Nome da marca a ser normalizado

    Returns:
        Nome da marca padronizado
    """
    if pd.isna(marca):
        return marca

    marca_upper = str(marca).strip().upper()

    # Verificar se existe um alias
    if marca_upper in MARCA_ALIASES:
        return MARCA_ALIASES[marca_upper]

    # Se nao houver alias, retornar o valor original (com strip)
    return str(marca).strip()


def ler_arquivo(arquivo: BytesIO, nome_arquivo: str) -> pd.DataFrame:
    """
    Le um arquivo Excel ou CSV e retorna um DataFrame.

    Args:
        arquivo: Buffer do arquivo carregado
        nome_arquivo: Nome do arquivo para detectar extensao

    Returns:
        DataFrame com os dados do arquivo

    Raises:
        DataValidationError: Se o formato do arquivo nao for suportado
    """
    nome_lower = nome_arquivo.lower()

    try:
        if nome_lower.endswith('.xlsx') or nome_lower.endswith('.xls'):
            # Usar openpyxl para xlsx, xlrd para xls antigo
            engine = 'openpyxl' if nome_lower.endswith('.xlsx') else None
            df = pd.read_excel(arquivo, engine=engine)
        elif nome_lower.endswith('.csv'):
            arquivo.seek(0)
            conteudo_bruto = arquivo.read()

            # Detectar encoding
            conteudo_texto = None
            encoding_usado = None
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']:
                try:
                    conteudo_texto = conteudo_bruto.decode(enc)
                    encoding_usado = enc
                    break
                except Exception:
                    continue

            if conteudo_texto is None:
                raise DataValidationError(
                    "Nao foi possivel decodificar o arquivo CSV. "
                    "Tente converter para Excel (.xlsx) antes de enviar."
                )

            # Detectar separador pela primeira linha
            primeira_linha = conteudo_texto.splitlines()[0]
            contagem = {
                '|': primeira_linha.count('|'),
                ';': primeira_linha.count(';'),
                ',': primeira_linha.count(','),
                '\t': primeira_linha.count('\t')
            }
            separador = max(contagem, key=contagem.get)
            if contagem[separador] == 0:
                separador = ','

            # Usar pandas para ler de forma robusta (respeita aspas, campos com separador, etc)
            try:
                df = pd.read_csv(
                    BytesIO(conteudo_bruto),
                    sep=separador,
                    encoding=encoding_usado,
                    dtype=str,
                    engine="python",
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                    keep_default_na=False,
                    on_bad_lines="skip",  # Pula linhas com problemas
                )
            except Exception:
                # Fallback: tentar autodetect de separador (caso a primeira linha engane)
                df = pd.read_csv(
                    BytesIO(conteudo_bruto),
                    sep=None,
                    encoding=encoding_usado,
                    dtype=str,
                    engine="python",
                    keep_default_na=False,
                    on_bad_lines="skip",
                )

            # Garantir string
            df = df.astype(str)
        else:
            raise DataValidationError(
                f"Formato de arquivo nao suportado: {nome_arquivo}. "
                "Use .xlsx, .xls ou .csv"
            )

        return df

    except Exception as e:
        if isinstance(e, DataValidationError):
            raise
        raise DataValidationError(f"Erro ao ler arquivo {nome_arquivo}: {str(e)}")


def validar_colunas(
    df: pd.DataFrame,
    colunas_obrigatorias: List[str],
    nome_planilha: str
) -> Tuple[bool, List[str]]:
    """
    Valida se as colunas obrigatorias existem no DataFrame.

    Args:
        df: DataFrame a ser validado
        colunas_obrigatorias: Lista de nomes de colunas obrigatorias
        nome_planilha: Nome da planilha para mensagens de erro

    Returns:
        Tupla (sucesso, lista_colunas_faltantes)
    """
    colunas_existentes = set(df.columns.str.strip())
    colunas_faltantes = []

    for col in colunas_obrigatorias:
        if col not in colunas_existentes:
            colunas_faltantes.append(col)

    return (len(colunas_faltantes) == 0, colunas_faltantes)


def processar_bd_produtos(arquivo: BytesIO, nome_arquivo: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Le e processa a planilha BD Produtos.

    Args:
        arquivo: Buffer do arquivo
        nome_arquivo: Nome do arquivo

    Returns:
        Tupla (DataFrame processado, lista de avisos)

    Raises:
        DataValidationError: Se colunas obrigatorias faltarem
    """
    avisos = []

    # Ler arquivo
    df = ler_arquivo(arquivo, nome_arquivo)

    # Normalizar nomes de colunas (remover espacos)
    df.columns = df.columns.str.strip()

    # Validar colunas obrigatorias
    valido, faltantes = validar_colunas(df, BD_REQUIRED_COLUMNS, "BD Produtos")
    if not valido:
        raise DataValidationError(
            f"Colunas obrigatorias faltando em BD Produtos: {', '.join(faltantes)}"
        )

    # Normalizar SKU
    df[COL_SKU_NORMALIZADO] = df[BD_COL_SKU].apply(normalizar_sku)

    # Normalizar Marca
    df[BD_COL_MARCA] = df[BD_COL_MARCA].apply(normalizar_marca)

    # Verificar marcas fora do conjunto esperado
    marcas_unicas = df[BD_COL_MARCA].dropna().unique()
    marcas_conhecidas = set([m.upper() for m in MARCAS_GRUPO] + list(MARCA_ALIASES.keys()))

    for marca in marcas_unicas:
        if str(marca).upper() not in marcas_conhecidas:
            avisos.append(f"Marca nao reconhecida encontrada: '{marca}'")

    # Remover linhas com SKU vazio apos normalizacao
    linhas_antes = len(df)
    df = df[df[COL_SKU_NORMALIZADO] != ""]
    linhas_removidas = linhas_antes - len(df)

    if linhas_removidas > 0:
        avisos.append(f"{linhas_removidas} linhas removidas por SKU vazio/invalido")

    # Verificar duplicatas de SKU
    duplicatas = df[df[COL_SKU_NORMALIZADO].duplicated(keep=False)]
    if len(duplicatas) > 0:
        skus_dup = duplicatas[COL_SKU_NORMALIZADO].unique()[:5]  # Mostrar ate 5
        avisos.append(
            f"SKUs duplicados encontrados: {', '.join(skus_dup)}... "
            f"(Total: {len(duplicatas)} linhas)"
        )

    return df, avisos


def processar_vendas(arquivo: BytesIO, nome_arquivo: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Le e processa a planilha de Vendas.

    Args:
        arquivo: Buffer do arquivo
        nome_arquivo: Nome do arquivo

    Returns:
        Tupla (DataFrame processado, lista de avisos)

    Raises:
        DataValidationError: Se colunas obrigatorias faltarem
    """
    avisos = []

    # Ler arquivo
    df = ler_arquivo(arquivo, nome_arquivo)

    # Normalizar nomes de colunas (remover espacos)
    df.columns = df.columns.str.strip()

    # Validar colunas obrigatorias
    valido, faltantes = validar_colunas(df, VENDAS_REQUIRED_COLUMNS, "Vendas")
    if not valido:
        raise DataValidationError(
            f"Colunas obrigatorias faltando em Vendas: {', '.join(faltantes)}"
        )

    # Verificar colunas opcionais
    for col in VENDAS_OPTIONAL_COLUMNS:
        if col not in df.columns:
            avisos.append(f"Coluna opcional '{col}' nao encontrada")
            df[col] = ""  # Adicionar coluna vazia

    # Normalizar CodigoProduto
    df[COL_CODIGO_PRODUTO_NORMALIZADO] = df[VENDAS_COL_CODIGO_PRODUTO].apply(normalizar_sku)

    # Contar registros por tipo
    contagem_tipos = df[VENDAS_COL_TIPO].value_counts()
    total_vendas = contagem_tipos.get(TIPO_VENDA, 0)
    total_outros = len(df) - total_vendas

    avisos.append(f"Total de registros: {len(df)}")
    avisos.append(f"Registros tipo 'Venda': {total_vendas}")
    avisos.append(f"Outros tipos: {total_outros}")

    return df, avisos


def criar_indice_sku(df_bd: pd.DataFrame) -> dict:
    """
    Cria um indice de SKUs para busca rapida.

    O indice mapeia SKU normalizado -> (Marca, Nome) do produto.
    Tambem cria versoes com zero a esquerda para match de 4 digitos.

    Args:
        df_bd: DataFrame do BD Produtos processado

    Returns:
        Dicionario {sku_normalizado: {'marca': str, 'nome': str}}
    """
    indice = {}

    for _, row in df_bd.iterrows():
        sku = row[COL_SKU_NORMALIZADO]
        if sku:
            indice[sku] = {
                'marca': row[BD_COL_MARCA],
                'nome': row[BD_COL_NOME]
            }

            # Se o SKU tem 5 digitos e comeca com 0, criar versao sem o zero
            # para facilitar match quando vendas vier sem o zero
            if len(sku) == 5 and sku.startswith('0'):
                sku_sem_zero = sku[1:]  # Remove o primeiro zero
                if sku_sem_zero not in indice:
                    # Nao sobrescrever se ja existir um SKU de 4 digitos
                    indice[sku_sem_zero] = {
                        'marca': row[BD_COL_MARCA],
                        'nome': row[BD_COL_NOME],
                        '_original_sku': sku  # Guardar referencia ao SKU original
                    }

    return indice


def buscar_sku(
    codigo_produto: str,
    indice_sku: dict
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Busca um codigo de produto no indice de SKUs.

    Estrategia de busca:
    1. Tentar match exato
    2. Se nao encontrar e o codigo tiver 4 digitos, tentar com zero a esquerda
    3. Se ainda nao encontrar, retornar NAO_ENCONTRADO

    Args:
        codigo_produto: Codigo do produto normalizado
        indice_sku: Indice de SKUs criado por criar_indice_sku()

    Returns:
        Tupla (marca, nome, motivo_match)
        - motivo_match: MATCH_EXATO, MATCH_COM_ZERO, ou NAO_ENCONTRADO
    """
    from .constants import (
        MOTIVO_MATCH_EXATO,
        MOTIVO_MATCH_COM_ZERO,
        MOTIVO_NAO_ENCONTRADO
    )

    if not codigo_produto:
        return None, None, MOTIVO_NAO_ENCONTRADO

    # 1. Tentar match exato
    if codigo_produto in indice_sku:
        info = indice_sku[codigo_produto]
        return info['marca'], info['nome'], MOTIVO_MATCH_EXATO

    # 2. Se codigo tem 4 digitos, tentar com zero a esquerda
    if len(codigo_produto) == 4:
        codigo_com_zero = '0' + codigo_produto
        if codigo_com_zero in indice_sku:
            info = indice_sku[codigo_com_zero]
            return info['marca'], info['nome'], MOTIVO_MATCH_COM_ZERO

    # 3. Nao encontrado
    return None, None, MOTIVO_NAO_ENCONTRADO


def carregar_bd_produtos_local(caminho: str = "data/bd_produtos.csv") -> Tuple[pd.DataFrame, List[str]]:
    """
    Carrega o BD Produtos de um arquivo CSV local fixo.

    Args:
        caminho: Caminho para o arquivo CSV (padrao: data/bd_produtos.csv)

    Returns:
        Tupla (DataFrame processado, lista de avisos)

    Raises:
        DataValidationError: Se arquivo nao existir ou colunas faltarem
    """
    import os

    avisos = []

    # Verificar se arquivo existe
    if not os.path.exists(caminho):
        raise DataValidationError(
            f"Arquivo BD Produtos nao encontrado: {caminho}"
        )

    # Ler CSV com diferentes encodings
    df = None
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(caminho, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        raise DataValidationError(
            f"Nao foi possivel ler o arquivo {caminho} com nenhum encoding"
        )

    # Normalizar nomes de colunas (remover espacos)
    df.columns = df.columns.str.strip()

    # Validar colunas obrigatorias
    valido, faltantes = validar_colunas(df, BD_REQUIRED_COLUMNS, "BD Produtos")
    if not valido:
        raise DataValidationError(
            f"Colunas obrigatorias faltando em BD Produtos: {', '.join(faltantes)}"
        )

    # Normalizar SKU
    df[COL_SKU_NORMALIZADO] = df[BD_COL_SKU].apply(normalizar_sku)

    # Normalizar Marca
    df[BD_COL_MARCA] = df[BD_COL_MARCA].apply(normalizar_marca)

    # Remover linhas com SKU vazio apos normalizacao
    linhas_antes = len(df)
    df = df[df[COL_SKU_NORMALIZADO] != ""]
    linhas_removidas = linhas_antes - len(df)

    if linhas_removidas > 0:
        avisos.append(f"{linhas_removidas} linhas removidas por SKU vazio/invalido")

    avisos.append(f"BD Produtos carregado: {len(df)} produtos")

    return df, avisos


def gerar_id_cliente(row: pd.Series) -> str:
    """
    Gera um identificador unico para o cliente/revendedor.

    Usa CodigoRevendedora como chave primaria.
    Se faltar, usa NomeRevendedora + Setor como fallback.

    Args:
        row: Linha do DataFrame de vendas

    Returns:
        String identificadora do cliente
    """
    from .constants import (
        VENDAS_COL_CODIGO_REVENDEDORA,
        VENDAS_COL_NOME_REVENDEDORA,
        VENDAS_COL_SETOR,
    )

    codigo = row.get(VENDAS_COL_CODIGO_REVENDEDORA)

    # Se codigo existe e nao e vazio
    if pd.notna(codigo) and str(codigo).strip():
        return str(codigo).strip()

    # Fallback: Nome + Setor
    nome = row.get(VENDAS_COL_NOME_REVENDEDORA, "")
    setor = row.get(VENDAS_COL_SETOR, "")

    return f"{nome}|{setor}"
