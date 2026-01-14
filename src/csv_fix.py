"""
csv_fix.py - Utilitários para correção de CSV quebrado.

Este módulo contém funções para reconstruir registros quebrados em CSVs
exportados de plataformas que dividem registros em múltiplas linhas.
"""

from typing import Tuple, Dict, Any, Optional
from io import StringIO
import csv


def fix_broken_csv_bytes(raw: bytes, *, sep: Optional[str] = None) -> Tuple[bytes, Dict[str, Any]]:
    """
    Corrige CSV quebrado: reconstrói registros divididos em múltiplas linhas
    e ajusta número de colunas para bater com o cabeçalho.
    
    Args:
        raw: Bytes brutos do CSV
        sep: Separador forçado (opcional). Se None, detecta automaticamente.
    
    Returns:
        Tupla (bytes_utf8_sem_bom, relatorio_dict)
        - bytes_utf8_sem_bom: CSV corrigido em UTF-8 sem BOM
        - relatorio_dict: Estatísticas e lista de correções aplicadas
    
    Raises:
        ValueError: Se o arquivo estiver vazio ou não puder ser corrigido
    """
    ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1", "windows-1252"]
    
    def detect_encoding(raw_bytes: bytes) -> str:
        """Detecta encoding tentando decodificar."""
        for enc in ENCODINGS:
            try:
                raw_bytes.decode(enc)
                return enc
            except Exception:
                continue
        return "utf-8"
    
    def detect_sep(first_line: str) -> str:
        """Detecta separador pela primeira linha (prioriza |, ;, ,, \\t)."""
        counts = {
            "|": first_line.count("|"),
            ";": first_line.count(";"),
            ",": first_line.count(","),
            "\t": first_line.count("\t"),
        }
        detected_sep = max(counts, key=counts.get)
        return detected_sep if counts[detected_sep] > 0 else ","
    
    def find_text_column(header: list) -> int:
        """
        Encontra índice da coluna de texto mais provável para absorver excesso.
        Prioriza: NomeProduto, Nome Material, NomeRevendedora, Nome, Descricao/Descrição.
        """
        header_lower = [h.lower().strip() for h in header]
        candidates = [
            "nomeproduto",
            "nome material",
            "nomerevendedora",
            "nome",
            "descricao",
            "descrição",
        ]
        for candidate in candidates:
            try:
                idx = header_lower.index(candidate)
                return idx
            except ValueError:
                continue
        # Fallback: primeira coluna
        return 0
    
    def split_naive(line: str, separator: str) -> list:
        """Divide linha pelo separador (método simples, não respeita aspas)."""
        return line.rstrip("\n").rstrip("\r").split(separator)
    
    # 1. Detectar encoding
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    lines = text.splitlines()
    
    if not lines:
        raise ValueError("Arquivo CSV vazio.")
    
    # 2. Detectar separador
    header_line = lines[0]
    separator = sep if sep else detect_sep(header_line)
    
    # 3. Parsear cabeçalho
    header_parts = split_naive(header_line, separator)
    header = [h.strip() for h in header_parts]
    expected_cols = len(header)
    
    if expected_cols == 0:
        raise ValueError("Cabeçalho CSV vazio ou inválido.")
    
    # 4. Encontrar coluna de texto para absorver excesso
    text_col_idx = find_text_column(header)
    
    # 5. Inicializar relatório
    report = {
        "encoding": encoding,
        "separator": separator,
        "expected_columns": expected_cols,
        "header": header,
        "text_column_used": header[text_col_idx],
        "fixes": [],
        "stats": {
            "total_original_lines": len(lines),
            "data_records_emitted": 0,
            "joined_broken_records": 0,
            "fixed_extra_cols": 0,
            "fixed_missing_cols": 0,
            "unchanged": 0,
        },
    }
    
    # 6. Usar csv.writer para escrever CSV corrigido corretamente
    # QUOTE_MINIMAL coloca aspas apenas quando necessário (ex: campo contém |)
    output = StringIO()
    writer = csv.writer(
        output,
        delimiter=separator,
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )
    
    # Escrever header
    writer.writerow(header)
    
    # 7. Processar linhas de dados
    i = 1  # Começa após header
    while i < len(lines):
        start_line_no = i + 1  # 1-based para relatório
        buf = lines[i]
        parts = split_naive(buf, separator)
        
        # 7a. Reconstruir registros quebrados (linhas que começam com separador)
        joined = 0
        while len(parts) < expected_cols and (i + 1) < len(lines):
            next_line = lines[i + 1]
            # Se próxima linha começa com separador, é continuação
            if next_line.startswith(separator):
                buf += next_line  # Concatena sem inserir nada
                i += 1
                joined += 1
                parts = split_naive(buf, separator)
            else:
                break
        
        if joined > 0:
            report["stats"]["joined_broken_records"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": "joined_continuation_lines",
                "joined_lines_count": joined,
            })
        
        # 7b. Ajustar número de colunas
        if len(parts) == expected_cols:
            # Linha correta, escrever como está
            writer.writerow(parts)
            report["stats"]["unchanged"] += 1
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue
        
        # Colunas a mais: absorver excesso na coluna de texto
        if len(parts) > expected_cols:
            extra = len(parts) - expected_cols
            
            # Dividir: antes da coluna de texto, coluna de texto + excesso, depois
            left = parts[:text_col_idx]
            merged = separator.join(parts[text_col_idx:text_col_idx + 1 + extra])
            right = parts[text_col_idx + 1 + extra:]
            
            new_parts = left + [merged] + right
            
            # Garantir tamanho exato
            if len(new_parts) > expected_cols:
                new_parts = new_parts[:expected_cols]
            elif len(new_parts) < expected_cols:
                new_parts += [""] * (expected_cols - len(new_parts))
            
            report["stats"]["fixed_extra_cols"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": f"merged_extra_columns_into_{header[text_col_idx]}",
                "original_col_count": len(parts),
                "final_col_count": len(new_parts),
            })
            writer.writerow(new_parts)
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue
        
        # Colunas a menos: preencher com ""
        if len(parts) < expected_cols:
            new_parts = parts + [""] * (expected_cols - len(parts))
            report["stats"]["fixed_missing_cols"] += 1
            report["fixes"].append({
                "line_number_start": start_line_no,
                "line_number_end": i + 1,
                "action": "padded_missing_columns",
                "original_col_count": len(parts),
                "final_col_count": len(new_parts),
            })
            writer.writerow(new_parts)
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue
    
    # 8. Converter para bytes UTF-8 sem BOM
    csv_corrigido_text = output.getvalue()
    csv_corrigido_bytes = csv_corrigido_text.encode("utf-8")
    
    return csv_corrigido_bytes, report
