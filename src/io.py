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
import json
from typing import Tuple, List, Optional, Set, Dict, Any
from io import BytesIO, StringIO

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


def corrigir_csv(raw: bytes, target_col: str = "NomeProduto") -> Tuple[bytes, Dict[str, Any]]:
    """
    Corrige CSV automaticamente: reconstrói registros quebrados e ajusta colunas.
    
    Args:
        raw: Bytes brutos do CSV
        target_col: Nome da coluna que absorve excesso quando houver colunas a mais
    
    Returns:
        Tupla (csv_corrigido_bytes, relatorio_dict)
    """
    ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1", "windows-1252"]
    
    def detect_encoding(raw_bytes: bytes) -> str:
        for enc in ENCODINGS:
            try:
                raw_bytes.decode(enc)
                return enc
            except Exception:
                continue
        return "utf-8"
    
    def detect_sep(first_line: str) -> str:
        counts = {
            "|": first_line.count("|"),
            ";": first_line.count(";"),
            ",": first_line.count(","),
            "\t": first_line.count("\t"),
        }
        sep = max(counts, key=counts.get)
        return sep if counts[sep] > 0 else ","
    
    def split_naive(line: str, sep: str):
        return line.rstrip("\n").rstrip("\r").split(sep)
    
    enc = detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    lines = text.splitlines()

    if not lines:
        raise ValueError("Arquivo vazio.")

    header_line = lines[0]
    sep = detect_sep(header_line)

    header = [h.strip() for h in split_naive(header_line, sep)]
    expected_cols = len(header)

    # índice da coluna alvo (para colunas a mais)
    try:
        target_idx = header.index(target_col)
    except ValueError:
        target_idx = 0  # fallback seguro

    report = {
        "encoding": enc,
        "separator": sep,
        "expected_columns": expected_cols,
        "header": header,
        "target_column": header[target_idx] if 0 <= target_idx < expected_cols else target_col,
        "fixes": [],
        "stats": {
            "total_original_lines_including_header": len(lines),
            "data_records_emitted": 0,
            "joined_broken_records": 0,
            "fixed_extra_cols": 0,
            "fixed_missing_cols": 0,
            "unchanged": 0,
        },
    }

    # Usar StringIO e csv.writer para escrever CSV corrigido corretamente
    output = StringIO()
    writer = csv.writer(output, delimiter=sep, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    
    # Escrever header
    writer.writerow(header)

    # --- 1) Reconstituir registros quebrados (linhas "continuação" começam com sep) ---
    i = 1  # começa após header
    while i < len(lines):
        start_line_no = i + 1  # 1-based
        buf = lines[i]
        parts = split_naive(buf, sep)

        # Se faltam colunas, tenta juntar com próximas linhas que parecem continuação
        joined = 0
        while len(parts) < expected_cols and (i + 1) < len(lines) and lines[i + 1].startswith(sep):
            buf += lines[i + 1]  # junta sem inserir nada
            i += 1
            joined += 1
            parts = split_naive(buf, sep)

        if joined > 0:
            report["stats"]["joined_broken_records"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": "joined_continuation_lines_starting_with_separator",
                "joined_lines_count": joined,
            })

        # --- 2) Ajuste final: colunas a mais / a menos (sem descartar) ---
        if len(parts) == expected_cols:
            writer.writerow(parts)
            report["stats"]["unchanged"] += 1
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue

        # colunas a mais: absorve excesso na coluna alvo
        if len(parts) > expected_cols:
            extra = len(parts) - expected_cols

            left = parts[:target_idx]
            merged = sep.join(parts[target_idx:target_idx + 1 + extra])
            right = parts[target_idx + 1 + extra:]

            new_parts = left + [merged] + right

            # normaliza tamanho
            if len(new_parts) > expected_cols:
                new_parts = new_parts[:expected_cols]
            elif len(new_parts) < expected_cols:
                new_parts += [""] * (expected_cols - len(new_parts))

            report["stats"]["fixed_extra_cols"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": f"merged_extra_columns_into_{header[target_idx]}",
                "original_col_count": len(parts),
                "final_col_count": len(new_parts),
            })
            writer.writerow(new_parts)
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue

        # colunas a menos: completa vazio
        if len(parts) < expected_cols:
            new_parts = parts + [""] * (expected_cols - len(parts))
            report["stats"]["fixed_missing_cols"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": "padded_missing_columns_with_empty_strings",
                "original_col_count": len(parts),
                "final_col_count": len(new_parts),
            })
            writer.writerow(new_parts)
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue

    csv_corrigido = output.getvalue().encode("utf-8")
    
    return csv_corrigido, report


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
                    keep_default_na=False,
                    on_bad_lines="error"  # NÃO pula linha - garante integridade dos dados
                )
            except Exception as e:
                # Tentar corrigir CSV automaticamente
                try:
                    # Detectar primeira coluna para usar como target (pode ser qualquer CSV)
                    primeira_linha = conteudo_texto.splitlines()[0]
                    header_cols = primeira_linha.split(separador)
                    target_col = header_cols[0].strip() if header_cols else "NomeProduto"
                    
                    csv_corrigido_bytes, relatorio = corrigir_csv(conteudo_bruto, target_col)
                    
                    # Tentar ler o CSV corrigido
                    df = pd.read_csv(
                        BytesIO(csv_corrigido_bytes),
                        sep=relatorio["separator"],
                        encoding=relatorio["encoding"],
                        dtype=str,
                        engine="python",
                        quotechar='"',
                        keep_default_na=False,
                        on_bad_lines="error"
                    )
                except Exception as e2:
                    raise DataValidationError(
                        "Erro ao importar CSV. "
                        "O arquivo possui linhas inconsistentes (ex: separador dentro do texto, aspas quebradas ou colunas a mais).\n\n"
                        "👉 Nenhuma linha foi descartada.\n"
                        "👉 Corrija o CSV ou converta para Excel (.xlsx).\n\n"
                        f"Detalhe técnico: {str(e2)[:300]}"
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
