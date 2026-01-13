"""
app.py - Interface principal Streamlit para Multimarks Active Circles.

Aplicacao para analise de revendedores ativos e multimarcas por ciclo,
cruzando planilhas de BD Produtos e Vendas.

Autor: Multimarks Analytics
"""

import streamlit as st
import pandas as pd
import hashlib
from io import BytesIO

# Importar modulos do projeto
from src.constants import (
    APP_TITLE,
    APP_SUBTITLE,
    VENDAS_COL_CICLO,
    VENDAS_COL_SETOR,
    COL_MARCA_BD,
    COL_IS_MULTIMARCAS,
    COL_CLIENTE_ID,
    MARCA_DESCONHECIDA,
)
from src.io import (
    processar_bd_produtos,
    processar_vendas,
    carregar_bd_produtos_local,
    DataValidationError,
)
from src.transform import (
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
from src.reports import (
    formatar_tabela_setor_ciclo,
    formatar_tabela_multimarcas,
    formatar_tabela_auditoria,
    gerar_resumo_metricas,
    formatar_valor,
    gerar_lista_clientes_para_selecao,
    calcular_estatisticas_ciclo,
)
from src.export import (
    exportar_csv,
    exportar_excel,
    gerar_nome_arquivo,
)


# =============================================================================
# CONFIGURACAO DA PAGINA
# =============================================================================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================
st.markdown("""
<style>
    /* Cards de metricas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        color: white;
        text-align: center;
        margin: 5px;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9em;
        opacity: 0.9;
    }

    /* Estilo para tabelas */
    .dataframe {
        font-size: 0.85em;
    }

    /* Header */
    .main-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }

    /* Sidebar */
    .css-1d391kg {
        background-color: #f8f9fa;
    }

    /* Botoes de download */
    .stDownloadButton > button {
        width: 100%;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CONFIGURACAO DO BD PRODUTOS (ARQUIVO FIXO)
# =============================================================================
BD_PRODUTOS_PATH = "data/bd_produtos.csv"


# =============================================================================
# FUNCOES DE CACHE
# =============================================================================
@st.cache_data(show_spinner=False)
def carregar_bd_produtos_cached():
    """
    Carrega o BD Produtos do arquivo fixo com cache.

    Returns:
        Tupla (DataFrame, lista de avisos)
    """
    return carregar_bd_produtos_local(BD_PRODUTOS_PATH)


@st.cache_data(show_spinner=False)
def processar_vendas_cached(vendas_bytes: bytes, vendas_nome: str, _df_bd):
    """
    Processa os dados de vendas com cache baseado no conteudo do arquivo.

    Args:
        vendas_bytes: Bytes do arquivo de vendas
        vendas_nome: Nome do arquivo
        _df_bd: DataFrame do BD Produtos (prefixo _ para nao usar no hash)

    Returns:
        Dicionario com todos os DataFrames processados e avisos
    """
    # Converter bytes para BytesIO
    vendas_buffer = BytesIO(vendas_bytes)

    avisos = []

    # Processar Vendas
    df_vendas, avisos_vendas = processar_vendas(vendas_buffer, vendas_nome)
    avisos.extend([f"[Vendas] {a}" for a in avisos_vendas])

    # Enriquecer vendas com marca
    df_vendas_enriquecido, avisos_enrich = enriquecer_vendas_com_marca(
        df_vendas, _df_bd
    )
    avisos.extend([f"[Enriquecimento] {a}" for a in avisos_enrich])

    # Filtrar apenas vendas
    df_vendas_filtrado = filtrar_vendas(df_vendas_enriquecido)

    # Calcular metricas por cliente
    df_clientes = calcular_metricas_cliente(df_vendas_filtrado)

    # Calcular metricas por setor/ciclo
    df_setor_ciclo = calcular_metricas_setor_ciclo(df_clientes)

    # Gerar auditoria
    df_auditoria = gerar_auditoria_skus(df_vendas_enriquecido)

    return {
        'df_vendas_enriquecido': df_vendas_enriquecido,
        'df_vendas_filtrado': df_vendas_filtrado,
        'df_clientes': df_clientes,
        'df_setor_ciclo': df_setor_ciclo,
        'df_auditoria': df_auditoria,
        'avisos': avisos
    }


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
def main():
    # Header
    st.title(f":chart_with_upwards_trend: {APP_TITLE}")
    st.markdown(f"*{APP_SUBTITLE}*")
    st.markdown("---")

    # ==========================================================================
    # CARREGAR BD PRODUTOS (AUTOMATICO)
    # ==========================================================================
    try:
        df_bd, avisos_bd = carregar_bd_produtos_cached()
        bd_carregado = True
    except DataValidationError as e:
        st.error(f":x: Erro ao carregar BD Produtos: {str(e)}")
        bd_carregado = False
        df_bd = None
        avisos_bd = []

    # ==========================================================================
    # SIDEBAR - Upload de Vendas
    # ==========================================================================
    with st.sidebar:
        st.header(":file_folder: Upload de Vendas")

        # Mostrar status do BD Produtos
        if bd_carregado:
            st.success(f":white_check_mark: BD Produtos: {len(df_bd)} produtos")
        else:
            st.error(":x: BD Produtos nao carregado")

        st.markdown("---")

        # Upload Vendas
        arquivo_vendas = st.file_uploader(
            "Planilha de Vendas",
            type=['xlsx', 'xls', 'csv'],
            key='vendas',
            help="Planilha de vendas com: Setor, NomeRevendedora, CodigoRevendedora, etc."
        )

        st.markdown("---")

        # Botao Processar
        processar = st.button(
            ":gear: Processar Dados",
            type="primary",
            use_container_width=True,
            disabled=(not bd_carregado or arquivo_vendas is None)
        )

    # ==========================================================================
    # PROCESSAMENTO
    # ==========================================================================
    if not bd_carregado:
        st.error(
            "O arquivo **BD Produtos** nao foi encontrado ou esta invalido. "
            "Verifique se o arquivo `data/bd_produtos.csv` existe no servidor."
        )
        return

    if arquivo_vendas is None:
        st.info(
            ":point_left: Faca upload da planilha de **Vendas** "
            "na barra lateral para comecar."
        )
        st.markdown("""
        ### Formato esperado da planilha de Vendas:

        | Setor | NomeRevendedora | CodigoRevendedora | CicloFaturamento | CodigoProduto | NomeProduto | Tipo | QuantidadeItens | ValorPraticado | MeioCaptacao |
        |-------|-----------------|-------------------|------------------|---------------|-------------|------|-----------------|----------------|--------------|
        | Norte | Maria Silva | 12345 | 202401 | 01234 | Produto X | Venda | 2 | 89.90 | Digital |
        """)
        return

    # Processar dados
    if processar or 'dados_processados' in st.session_state:
        if processar:
            with st.spinner("Processando dados... Isso pode levar alguns segundos."):
                try:
                    # Ler bytes do arquivo de vendas
                    vendas_bytes = arquivo_vendas.getvalue()

                    # Processar com cache
                    dados = processar_vendas_cached(
                        vendas_bytes,
                        arquivo_vendas.name,
                        df_bd
                    )

                    # Adicionar avisos do BD aos dados
                    dados['avisos'] = [f"[BD] {a}" for a in avisos_bd] + dados['avisos']
                    dados['df_bd'] = df_bd

                    st.session_state['dados_processados'] = dados
                    st.success(":white_check_mark: Dados processados com sucesso!")

                except DataValidationError as e:
                    st.error(f":x: Erro de validacao: {str(e)}")
                    return
                except Exception as e:
                    st.error(f":x: Erro inesperado: {str(e)}")
                    return

        # Recuperar dados processados
        if 'dados_processados' not in st.session_state:
            st.warning("Clique em 'Processar Dados' para iniciar a analise.")
            return

        dados = st.session_state['dados_processados']

        # Exibir avisos
        if dados['avisos']:
            with st.expander(":information_source: Avisos do processamento", expanded=False):
                for aviso in dados['avisos']:
                    if 'ALERTA' in aviso:
                        st.warning(aviso)
                    else:
                        st.info(aviso)

        # ======================================================================
        # FILTROS NA SIDEBAR
        # ======================================================================
        with st.sidebar:
            st.markdown("---")
            st.header(":mag: Filtros")

            # Obter valores unicos
            ciclos_disponiveis = sorted(
                dados['df_vendas_filtrado'][VENDAS_COL_CICLO].dropna().unique().tolist()
            )
            setores_disponiveis = sorted(
                dados['df_vendas_filtrado'][VENDAS_COL_SETOR].dropna().unique().tolist()
            )
            marcas_disponiveis = sorted([
                m for m in dados['df_vendas_filtrado'][COL_MARCA_BD].dropna().unique().tolist()
                if m != MARCA_DESCONHECIDA
            ])

            # Filtro de ciclos
            ciclos_selecionados = st.multiselect(
                "Ciclos",
                options=ciclos_disponiveis,
                default=ciclos_disponiveis,
                help="Selecione os ciclos de faturamento"
            )

            # Filtro de setores
            setores_selecionados = st.multiselect(
                "Setores",
                options=setores_disponiveis,
                default=[],
                help="Deixe vazio para todos os setores"
            )

            # Filtro de marcas
            marcas_selecionadas = st.multiselect(
                "Marcas",
                options=marcas_disponiveis,
                default=[],
                help="Deixe vazio para todas as marcas"
            )

            # Checkbox multimarcas
            apenas_multimarcas = st.checkbox(
                "Somente Multimarcas",
                value=False,
                help="Filtrar apenas clientes que compraram 2+ marcas"
            )

        # ======================================================================
        # APLICAR FILTROS
        # ======================================================================
        df_vendas_filtrado = aplicar_filtros(
            dados['df_vendas_filtrado'],
            ciclos=ciclos_selecionados if ciclos_selecionados else None,
            setores=setores_selecionados if setores_selecionados else None,
            marcas=marcas_selecionadas if marcas_selecionadas else None
        )

        df_clientes_filtrado = aplicar_filtros(
            dados['df_clientes'],
            ciclos=ciclos_selecionados if ciclos_selecionados else None,
            setores=setores_selecionados if setores_selecionados else None,
            apenas_multimarcas=apenas_multimarcas
        )

        df_setor_ciclo_filtrado = aplicar_filtros(
            dados['df_setor_ciclo'],
            ciclos=ciclos_selecionados if ciclos_selecionados else None,
            setores=setores_selecionados if setores_selecionados else None
        )

        # ======================================================================
        # TABS PRINCIPAIS
        # ======================================================================
        tab_visao, tab_multi, tab_novos, tab_audit, tab_cliente = st.tabs([
            ":bar_chart: Visao Geral",
            ":star: Multimarcas",
            ":new: Produtos Novos",
            ":mag: Auditoria",
            ":bust_in_silhouette: Detalhe Cliente"
        ])

        # ======================================================================
        # TAB: VISAO GERAL
        # ======================================================================
        with tab_visao:
            st.subheader("Metricas Gerais")

            # Calcular metricas
            metricas = calcular_metricas_gerais(df_clientes_filtrado, df_vendas_filtrado)

            # Exibir cards de metricas
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    label="Clientes Ativos",
                    value=f"{metricas['total_ativos']:,}"
                )
            with col2:
                st.metric(
                    label="Multimarcas",
                    value=f"{metricas['total_multimarcas']:,}"
                )
            with col3:
                st.metric(
                    label="% Multimarcas",
                    value=f"{metricas['percent_multimarcas']:.1f}%"
                )
            with col4:
                st.metric(
                    label="Total Itens",
                    value=f"{metricas['total_itens']:,.0f}"
                )
            with col5:
                st.metric(
                    label="Valor Total",
                    value=f"R$ {metricas['total_valor']:,.2f}"
                )

            st.markdown("---")

            # Top Setores
            col_top1, col_top2 = st.columns(2)

            top_valor, top_ativos = calcular_top_setores(df_setor_ciclo_filtrado)

            with col_top1:
                st.subheader(":trophy: Top 5 Setores por Valor")
                if not top_valor.empty:
                    top_valor_fmt = top_valor.copy()
                    top_valor_fmt['ValorTotal'] = top_valor_fmt['ValorTotal'].apply(
                        lambda x: f"R$ {x:,.2f}"
                    )
                    top_valor_fmt.columns = ['Setor', 'Valor Total']
                    st.dataframe(top_valor_fmt, use_container_width=True, hide_index=True)
                else:
                    st.info("Sem dados para exibir")

            with col_top2:
                st.subheader(":busts_in_silhouette: Top 5 Setores por Clientes")
                if not top_ativos.empty:
                    top_ativos_fmt = top_ativos.copy()
                    top_ativos_fmt['ClientesAtivos'] = top_ativos_fmt['ClientesAtivos'].astype(int)
                    top_ativos_fmt.columns = ['Setor', 'Clientes Ativos']
                    st.dataframe(top_ativos_fmt, use_container_width=True, hide_index=True)
                else:
                    st.info("Sem dados para exibir")

            st.markdown("---")

            # Tabela por Ciclo
            st.subheader(":calendar: Resumo por Ciclo")
            if not df_setor_ciclo_filtrado.empty:
                df_ciclo = calcular_estatisticas_ciclo(df_setor_ciclo_filtrado)
                st.dataframe(df_ciclo, use_container_width=True, hide_index=True)

            st.markdown("---")

            # Tabela Ativos por Setor e Ciclo
            st.subheader(":chart_with_upwards_trend: Ativos por Setor e Ciclo")
            if not df_setor_ciclo_filtrado.empty:
                df_setor_fmt = formatar_tabela_setor_ciclo(df_setor_ciclo_filtrado)
                st.dataframe(df_setor_fmt, use_container_width=True, hide_index=True)

                # Botoes de download
                col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
                with col_dl1:
                    st.download_button(
                        ":arrow_down: CSV",
                        data=exportar_csv(df_setor_fmt),
                        file_name=gerar_nome_arquivo("ativos_setor_ciclo", "csv"),
                        mime="text/csv"
                    )
                with col_dl2:
                    st.download_button(
                        ":arrow_down: Excel",
                        data=exportar_excel(df_setor_fmt, "Ativos"),
                        file_name=gerar_nome_arquivo("ativos_setor_ciclo", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("Sem dados para os filtros selecionados")

        # ======================================================================
        # TAB: MULTIMARCAS
        # ======================================================================
        with tab_multi:
            st.subheader(":star: Clientes Multimarcas")

            # Filtrar multimarcas
            df_multi = df_clientes_filtrado[df_clientes_filtrado[COL_IS_MULTIMARCAS] == True]

            if not df_multi.empty:
                st.info(f"Total de clientes multimarcas: **{len(df_multi):,}**")

                df_multi_fmt = formatar_tabela_multimarcas(df_multi)
                st.dataframe(df_multi_fmt, use_container_width=True, hide_index=True)

                # Botoes de download
                col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
                with col_dl1:
                    st.download_button(
                        ":arrow_down: CSV",
                        data=exportar_csv(df_multi_fmt),
                        file_name=gerar_nome_arquivo("clientes_multimarcas", "csv"),
                        mime="text/csv",
                        key="dl_multi_csv"
                    )
                with col_dl2:
                    st.download_button(
                        ":arrow_down: Excel",
                        data=exportar_excel(df_multi_fmt, "Multimarcas"),
                        file_name=gerar_nome_arquivo("clientes_multimarcas", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_multi_xlsx"
                    )

                # Analise de combinacoes de marcas
                st.markdown("---")
                st.subheader(":link: Combinacoes de Marcas mais Frequentes")

                combinacoes = df_multi_fmt['Marcas'].value_counts().head(10).reset_index()
                combinacoes.columns = ['Combinacao de Marcas', 'Quantidade']
                st.dataframe(combinacoes, use_container_width=True, hide_index=True)

            else:
                st.info("Nenhum cliente multimarcas encontrado para os filtros selecionados.")

        # ======================================================================
        # TAB: PRODUTOS NOVOS (NAO CADASTRADOS)
        # ======================================================================
        with tab_novos:
            st.subheader(":new: Produtos Novos / Lancamentos")
            st.markdown("""
            Produtos que aparecem na planilha de **Vendas** mas **nao estao cadastrados**
            no BD Produtos. Podem ser lancamentos recentes que precisam ser adicionados ao cadastro.
            """)

            # Gerar relatorio de produtos nao cadastrados
            df_nao_cadastrados = gerar_produtos_nao_cadastrados(dados['df_vendas_enriquecido'])

            # Filtrar pelos ciclos selecionados se houver
            if ciclos_selecionados and not df_nao_cadastrados.empty:
                # Filtrar produtos que aparecem nos ciclos selecionados
                mask = df_nao_cadastrados['Ciclos'].apply(
                    lambda x: any(c in x for c in [str(c) for c in ciclos_selecionados])
                )
                df_nao_cadastrados = df_nao_cadastrados[mask]

            if not df_nao_cadastrados.empty:
                # Metricas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Produtos Nao Cadastrados",
                        f"{len(df_nao_cadastrados):,}"
                    )
                with col2:
                    st.metric(
                        "Total de Itens Vendidos",
                        f"{df_nao_cadastrados['Total_Itens'].sum():,.0f}"
                    )
                with col3:
                    st.metric(
                        "Valor Total",
                        f"R$ {df_nao_cadastrados['Valor_Total'].sum():,.2f}"
                    )

                st.markdown("---")
                st.markdown("""
                **Dica:** Use esta tabela para identificar produtos que precisam ser
                cadastrados no BD Produtos. O SKU e Nome vem da planilha de Vendas.
                """)

                # Formatar tabela para exibicao
                df_novos_fmt = df_nao_cadastrados.copy()
                df_novos_fmt['Valor_Total'] = df_novos_fmt['Valor_Total'].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                df_novos_fmt.columns = [
                    'SKU', 'Nome do Produto', 'Qtde Vendas', 'Total Itens',
                    'Valor Total', 'Ciclos', 'Setores'
                ]

                st.dataframe(df_novos_fmt, use_container_width=True, hide_index=True)

                # Botoes de download
                col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
                with col_dl1:
                    # Preparar dados para download (sem formatacao de moeda)
                    df_download = df_nao_cadastrados.copy()
                    df_download.columns = [
                        'SKU', 'Nome_Produto', 'Qtde_Vendas', 'Total_Itens',
                        'Valor_Total', 'Ciclos', 'Setores'
                    ]
                    st.download_button(
                        ":arrow_down: CSV",
                        data=exportar_csv(df_download),
                        file_name=gerar_nome_arquivo("produtos_nao_cadastrados", "csv"),
                        mime="text/csv",
                        key="dl_novos_csv"
                    )
                with col_dl2:
                    st.download_button(
                        ":arrow_down: Excel",
                        data=exportar_excel(df_download, "ProdutosNovos"),
                        file_name=gerar_nome_arquivo("produtos_nao_cadastrados", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_novos_xlsx"
                    )

            else:
                st.success(":white_check_mark: Todos os produtos vendidos estao cadastrados no BD Produtos!")

        # ======================================================================
        # TAB: AUDITORIA
        # ======================================================================
        with tab_audit:
            st.subheader(":mag: Auditoria de SKUs")

            # Filtrar auditoria pelos ciclos selecionados
            df_audit = dados['df_auditoria'].copy()
            if ciclos_selecionados:
                df_audit = df_audit[df_audit[VENDAS_COL_CICLO].isin(ciclos_selecionados)]

            if not df_audit.empty:
                # Resumo
                nao_encontrados = len(df_audit[df_audit['Motivo'] == 'NAO_ENCONTRADO'])
                match_zero = len(df_audit[df_audit['Motivo'] == 'MATCH_COM_ZERO'])

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SKUs Nao Encontrados", f"{nao_encontrados:,}")
                with col2:
                    st.metric("Match com Zero a Esquerda", f"{match_zero:,}")

                st.markdown("---")

                df_audit_fmt = formatar_tabela_auditoria(df_audit)
                st.dataframe(df_audit_fmt, use_container_width=True, hide_index=True)

                # Botoes de download
                col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
                with col_dl1:
                    st.download_button(
                        ":arrow_down: CSV",
                        data=exportar_csv(df_audit_fmt),
                        file_name=gerar_nome_arquivo("auditoria_skus", "csv"),
                        mime="text/csv",
                        key="dl_audit_csv"
                    )
                with col_dl2:
                    st.download_button(
                        ":arrow_down: Excel",
                        data=exportar_excel(df_audit_fmt, "Auditoria"),
                        file_name=gerar_nome_arquivo("auditoria_skus", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_audit_xlsx"
                    )
            else:
                st.success(":white_check_mark: Todos os SKUs foram encontrados no BD Produtos!")

        # ======================================================================
        # TAB: DETALHE CLIENTE
        # ======================================================================
        with tab_cliente:
            st.subheader(":bust_in_silhouette: Detalhamento por Cliente")

            # Lista de clientes para selecao
            lista_clientes = gerar_lista_clientes_para_selecao(df_clientes_filtrado)

            if lista_clientes:
                # Criar opcoes para selectbox
                opcoes = {c['label']: c['id'] for c in lista_clientes}

                cliente_selecionado_label = st.selectbox(
                    "Selecione um cliente",
                    options=list(opcoes.keys()),
                    help="Busque pelo codigo ou nome do revendedor"
                )

                if cliente_selecionado_label:
                    cliente_id = opcoes[cliente_selecionado_label]

                    # Obter detalhes
                    df_detalhe, resumo = obter_detalhe_cliente(
                        dados['df_vendas_enriquecido'],
                        cliente_id,
                        ciclo=ciclos_selecionados[0] if len(ciclos_selecionados) == 1 else None
                    )

                    # Exibir resumo
                    st.markdown("---")
                    st.subheader("Resumo do Cliente")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Marcas Distintas", resumo['marcas_distintas'])
                    with col2:
                        st.metric("Total Itens", f"{resumo['total_itens']:,.0f}")
                    with col3:
                        st.metric("Valor Total", f"R$ {resumo['total_valor']:,.2f}")
                    with col4:
                        st.metric("Ciclos", len(resumo['ciclos']))

                    # Lista de marcas
                    if resumo['marcas_lista']:
                        marcas_str = ", ".join([
                            m for m in resumo['marcas_lista'] if m != MARCA_DESCONHECIDA
                        ])
                        st.info(f":label: **Marcas compradas:** {marcas_str}")

                    # Tabela de itens
                    st.markdown("---")
                    st.subheader("Itens Comprados")

                    if not df_detalhe.empty:
                        st.dataframe(df_detalhe, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum item encontrado para este cliente.")
            else:
                st.info("Nenhum cliente encontrado para os filtros selecionados.")


# =============================================================================
# EXECUCAO
# =============================================================================
if __name__ == "__main__":
    main()
