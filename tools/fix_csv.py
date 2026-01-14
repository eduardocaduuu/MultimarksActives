#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path
from io import BytesIO

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1", "windows-1252"]

def detect_encoding(raw: bytes) -> str:
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
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

def fix_csv(raw: bytes, target_col: str = "NomeProduto") -> tuple:
    """
    Corrige CSV automaticamente: reconstrói registros quebrados e ajusta colunas.
    
    Returns:
        Tupla (csv_corrigido_bytes, relatorio_dict)
    """
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

    fixed_rows = [sep.join(header)]

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
            fixed_rows.append(sep.join(parts))
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
            fixed_rows.append(sep.join(new_parts))
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
            fixed_rows.append(sep.join(new_parts))
            report["stats"]["data_records_emitted"] += 1
            i += 1
            continue

    csv_corrigido = "\n".join(fixed_rows).encode("utf-8")
    
    return csv_corrigido, report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=False)
    ap.add_argument("--report", required=False)
    ap.add_argument("--target-col", default="NomeProduto", help="Coluna que absorve excesso quando houver colunas a mais")
    args = ap.parse_args()

    in_path = Path(args.input)
    raw = in_path.read_bytes()
    
    csv_corrigido, report = fix_csv(raw, args.target_col)
    
    report["input"] = str(in_path)
    
    out_csv = args.output or str(in_path.with_name(in_path.stem + "_corrigido.csv"))
    out_report = args.report or str(in_path.with_name(in_path.stem + "_relatorio_fix.json"))

    Path(out_csv).write_bytes(csv_corrigido)
    Path(out_report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK")
    print(f"Encoding: {report['encoding']}")
    print(f"Separador: {report['separator']!r}")
    print(f"Colunas esperadas: {report['expected_columns']}")
    print(f"Registros emitidos: {report['stats']['data_records_emitted']}")
    print(f"Registros juntados (quebra de linha): {report['stats']['joined_broken_records']}")
    print(f"Corrigidos (colunas a mais): {report['stats']['fixed_extra_cols']}")
    print(f"Corrigidos (colunas a menos): {report['stats']['fixed_missing_cols']}")
    print(f"CSV corrigido: {out_csv}")
    print(f"Relatório: {out_report}")

if __name__ == "__main__":
    main()
