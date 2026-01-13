"""
src - Modulo principal da aplicacao Multimarks Active Circles.

Este pacote contem os modulos de processamento de dados:
- constants: Constantes e configuracoes
- io: Leitura e validacao de dados
- transform: Transformacao e metricas
- reports: Geracao de relatorios
- export: Exportacao de dados
"""

from .constants import *
from .io import (
    normalizar_sku,
    normalizar_marca,
    ler_arquivo,
    validar_colunas,
    processar_bd_produtos,
    processar_vendas,
    carregar_bd_produtos_local,
    criar_indice_sku,
    buscar_sku,
    gerar_id_cliente,
    DataValidationError,
)
from .transform import (
    enriquecer_vendas_com_marca,
    filtrar_vendas,
    calcular_metricas_cliente,
    calcular_metricas_setor_ciclo,
    calcular_metricas_gerais,
    calcular_top_setores,
    obter_detalhe_cliente,
    gerar_auditoria_skus,
    gerar_produtos_nao_cadastrados,
    aplicar_filtros,
)
from .reports import (
    formatar_tabela_setor_ciclo,
    formatar_tabela_multimarcas,
    formatar_tabela_auditoria,
    gerar_resumo_metricas,
    formatar_valor,
    gerar_lista_clientes_para_selecao,
    calcular_estatisticas_ciclo,
)
from .export import (
    exportar_csv,
    exportar_excel,
    exportar_multiplas_abas,
    gerar_nome_arquivo,
)
