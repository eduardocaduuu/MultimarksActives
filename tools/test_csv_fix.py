#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para fix_broken_csv_bytes.

Testa a correção de CSV quebrado com um exemplo real.

REQUISITOS:
- Executar no ambiente virtual da aplicação (onde pandas está instalado)
- Ou instalar dependências: pip install pandas

USO:
    python tools/test_csv_fix.py
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.csv_fix import fix_broken_csv_bytes
    from io import BytesIO
    import pandas as pd
except ImportError as e:
    print(f"❌ ERRO: Módulo não encontrado: {e}")
    print("💡 Execute no ambiente virtual da aplicação ou instale dependências:")
    print("   pip install pandas")
    sys.exit(1)


def test_csv_fix():
    """Testa a correção de CSV quebrado."""
    
    # CSV de exemplo quebrado (registro dividido em múltiplas linhas)
    csv_quebrado = """Setor|NomeRevendedora|CodigoRevendedora|CicloFaturamento|CodigoProduto|NomeProduto|Tipo|QuantidadeItens|ValorPraticado
Norte|João Silva|123|202401|00123|Produto A|Venda|10|100.50
Sul|Maria Santos|456|202401|00456|Produto B
|Venda|5|50.25
Leste|Pedro Costa|789|202401|00789|Produto C|Venda|3|30.00|EXTRA_COL
Oeste|Ana Lima|012|202401|00012|Produto D|Venda|2|20.00
""".encode('utf-8')
    
    print("🧪 Testando correção de CSV quebrado...")
    print(f"📊 CSV original tem {len(csv_quebrado)} bytes")
    
    try:
        # Corrigir CSV
        csv_corrigido_bytes, relatorio = fix_broken_csv_bytes(csv_quebrado)
        
        print(f"✅ CSV corrigido tem {len(csv_corrigido_bytes)} bytes")
        print(f"📋 Separador detectado: {relatorio['separator']!r}")
        print(f"📋 Encoding detectado: {relatorio['encoding']}")
        print(f"📋 Colunas esperadas: {relatorio['expected_columns']}")
        print(f"📋 Coluna de texto usada: {relatorio['text_column_used']}")
        
        stats = relatorio['stats']
        print(f"\n📊 Estatísticas:")
        print(f"  - Linhas originais: {stats['total_original_lines']}")
        print(f"  - Registros emitidos: {stats['data_records_emitted']}")
        print(f"  - Registros juntados: {stats['joined_broken_records']}")
        print(f"  - Linhas com colunas a mais corrigidas: {stats['fixed_extra_cols']}")
        print(f"  - Linhas com colunas a menos corrigidas: {stats['fixed_missing_cols']}")
        print(f"  - Linhas inalteradas: {stats['unchanged']}")
        
        # Tentar ler CSV corrigido com pandas
        print(f"\n🔍 Tentando ler CSV corrigido com pandas...")
        df = pd.read_csv(
            BytesIO(csv_corrigido_bytes),
            sep=relatorio['separator'],
            encoding='utf-8',
            dtype=str,
            engine='python',
            quotechar='"',
            keep_default_na=False,
            on_bad_lines='error'
        )
        
        print(f"✅ CSV corrigido lido com sucesso!")
        print(f"📊 DataFrame tem {len(df)} linhas e {len(df.columns)} colunas")
        print(f"📋 Colunas: {list(df.columns)}")
        
        # Validar que todas as linhas têm o número correto de colunas
        expected_cols = relatorio['expected_columns']
        if len(df.columns) == expected_cols:
            print(f"✅ Todas as linhas têm {expected_cols} colunas (correto)")
        else:
            print(f"❌ ERRO: Esperado {expected_cols} colunas, mas DataFrame tem {len(df.columns)}")
            return False
        
        # Mostrar correções aplicadas
        if relatorio['fixes']:
            print(f"\n🔧 Correções aplicadas:")
            for i, fix in enumerate(relatorio['fixes'][:5], 1):  # Mostrar até 5
                print(f"  {i}. Linha {fix['line_number_start']}-{fix['line_number_end']}: {fix['action']}")
            if len(relatorio['fixes']) > 5:
                print(f"  ... e mais {len(relatorio['fixes']) - 5} correções")
        
        print(f"\n✅ Teste passou com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO no teste: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_continues_working():
    """Garante que upload Excel continua funcionando (teste manual)."""
    print("\n📝 NOTA: Teste de Excel deve ser feito manualmente no app Streamlit")
    print("   - Faça upload de um arquivo Excel (.xlsx)")
    print("   - Verifique que o processamento funciona normalmente")
    print("   - Não deve haver regressão na funcionalidade Excel")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE CORREÇÃO DE CSV QUEBRADO")
    print("=" * 60)
    
    sucesso = test_csv_fix()
    test_excel_continues_working()
    
    print("\n" + "=" * 60)
    if sucesso:
        print("✅ TODOS OS TESTES PASSARAM")
        sys.exit(0)
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        sys.exit(1)
