"""
app.py - Interface principal Streamlit para Multimarks Active Circles.

Aplicacao para analise de revendedores ativos e multimarcas por ciclo,
cruzando planilhas de BD Produtos e Vendas.

Autor: Multimarks Analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import json

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
    BD_IAF_PATH,
)
from src.io import (
    processar_bd_produtos,
    processar_vendas,
    carregar_bd_produtos_local,
    carregar_bd_iaf_local,
    corrigir_csv,
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
    cruzar_vendas_com_iaf,
)
from src.reports import (
    formatar_tabela_setor_ciclo,
    formatar_tabela_multimarcas,
    formatar_tabela_auditoria,
    formatar_tabela_iaf,
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
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# CSS CUSTOMIZADO - TEMA ESCURO
# =============================================================================
st.markdown("""
<style>
    /* Importar fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Reset e base */
    * {
        font-family: 'Inter', sans-serif;
    }

    /* Container principal */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Cards de metricas customizados */
    .metric-container {
        background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(108, 99, 255, 0.2);
        transition: all 0.3s ease;
    }
    .metric-container:hover {
        border-color: rgba(108, 99, 255, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(108, 99, 255, 0.15);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #6C63FF;
        margin: 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #A0A0A0;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-delta-positive {
        color: #00D26A;
        font-size: 0.85rem;
    }
    .metric-delta-negative {
        color: #FF6B6B;
        font-size: 0.85rem;
    }

    /* Headers */
    h1, h2, h3 {
        color: #FAFAFA !important;
    }

    /* Estilo para as tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1E1E2E;
        padding: 0.5rem;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: transparent;
        border-radius: 8px;
        color: #A0A0A0;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(108, 99, 255, 0.1);
        color: #FAFAFA;
    }
    .stTabs [aria-selected="true"] {
        background-color: #6C63FF !important;
        color: #FAFAFA !important;
    }

    /* Botoes */
    .stButton > button {
        background: linear-gradient(135deg, #6C63FF 0%, #5A52E0 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(108, 99, 255, 0.4);
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #2D2D44 0%, #1E1E2E 100%);
        border: 1px solid rgba(108, 99, 255, 0.3);
        color: #FAFAFA;
    }
    .stDownloadButton > button:hover {
        border-color: #6C63FF;
        background: linear-gradient(135deg, #3D3D54 0%, #2E2E3E 100%);
    }

    /* File uploader */
    .stFileUploader {
        background-color: #1E1E2E;
        border-radius: 12px;
        padding: 1rem;
        border: 2px dashed rgba(108, 99, 255, 0.3);
    }
    .stFileUploader:hover {
        border-color: #6C63FF;
    }

    /* Dataframes */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1E1E2E;
        border-radius: 8px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid #1E1E2E;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #FAFAFA;
    }

    /* Cards de info */
    .info-card {
        background: #1E1E2E;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        border-left: 4px solid #6C63FF;
        margin: 1rem 0;
    }

    /* Success/Error/Warning boxes */
    .stAlert {
        border-radius: 12px;
    }

    /* Selectbox e multiselect */
    .stSelectbox, .stMultiSelect {
        background-color: #1E1E2E;
        border-radius: 8px;
    }

    /* Checkbox */
    .stCheckbox {
        color: #FAFAFA;
    }

    /* Dividers */
    hr {
        border-color: #2D2D44;
        margin: 2rem 0;
    }

    /* Title styling */
    .main-title {
        background: linear-gradient(90deg, #6C63FF, #A855F7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
    }

    /* Subtitle */
    .subtitle {
        color: #A0A0A0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-success {
        background-color: rgba(0, 210, 106, 0.2);
        color: #00D26A;
    }
    .status-warning {
        background-color: rgba(255, 193, 7, 0.2);
        color: #FFC107;
    }
    .status-error {
        background-color: rgba(255, 107, 107, 0.2);
        color: #FF6B6B;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CONFIGURACAO DO BD PRODUTOS (ARQUIVO FIXO)
# =============================================================================
BD_PRODUTOS_PATH = "data/bd_produtos.csv"

# Cores para graficos
COLORS = {
    'primary': '#6C63FF',
    'secondary': '#A855F7',
    'success': '#00D26A',
    'warning': '#FFC107',
    'danger': '#FF6B6B',
    'info': '#00B4D8',
    'background': '#1E1E2E',
    'text': '#FAFAFA',
    'muted': '#A0A0A0'
}

CHART_COLORS = ['#6C63FF', '#A855F7', '#00D26A', '#00B4D8', '#FFC107', '#FF6B6B', '#FF8C42', '#4ECDC4']


# =============================================================================
# FUNCOES DE CACHE
# =============================================================================
@st.cache_data(show_spinner=False)
def carregar_bd_produtos_cached():
    """Carrega o BD Produtos do arquivo fixo com cache."""
    return carregar_bd_produtos_local(BD_PRODUTOS_PATH)


@st.cache_data(show_spinner=False)
def carregar_bd_iaf_cached():
    """Carrega o BD IAF do arquivo fixo com cache."""
    return carregar_bd_iaf_local(BD_IAF_PATH)


@st.cache_data(show_spinner=False)
def processar_vendas_cached(vendas_bytes: bytes, vendas_nome: str, _df_bd):
    """Processa os dados de vendas com cache."""
    vendas_buffer = BytesIO(vendas_bytes)
    avisos = []

    df_vendas, avisos_vendas = processar_vendas(vendas_buffer, vendas_nome)
    avisos.extend([f"[Vendas] {a}" for a in avisos_vendas])

    df_vendas_enriquecido, avisos_enrich = enriquecer_vendas_com_marca(df_vendas, _df_bd)
    avisos.extend([f"[Enriquecimento] {a}" for a in avisos_enrich])

    df_vendas_filtrado = filtrar_vendas(df_vendas_enriquecido)
    df_clientes = calcular_metricas_cliente(df_vendas_filtrado)
    df_setor_ciclo = calcular_metricas_setor_ciclo(df_clientes)
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
# FUNCOES DE GRAFICOS
# =============================================================================
def criar_grafico_pizza_multimarcas(total_ativos, total_multimarcas):
    """Cria grafico de pizza para multimarcas vs mono marca."""
    mono_marca = total_ativos - total_multimarcas

    fig = go.Figure(data=[go.Pie(
        labels=['Multimarcas', 'Mono Marca'],
        values=[total_multimarcas, mono_marca],
        hole=0.6,
        marker_colors=[COLORS['primary'], COLORS['muted']],
        textinfo='percent',
        textfont_size=14,
        textfont_color='white'
    )])

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(color='white')
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=60, l=20, r=20),
        height=300,
        annotations=[dict(
            text=f'{total_multimarcas}',
            x=0.5, y=0.5,
            font_size=28,
            font_color=COLORS['primary'],
            showarrow=False
        )]
    )

    return fig


def criar_grafico_barras_setores(df_setor_ciclo, top_n=10):
    """Cria grafico de barras vertical para top setores."""
    df_agg = df_setor_ciclo.groupby(VENDAS_COL_SETOR).agg({
        'ClientesAtivos': 'sum',
        'ValorTotal': 'sum'
    }).reset_index()

    # Top N ordenado do maior para menor
    df_top = df_agg.nlargest(top_n, 'ValorTotal').reset_index(drop=True)

    fig = go.Figure()

    # Cores em gradiente
    cores = [COLORS['primary']] * len(df_top)

    fig.add_trace(go.Bar(
        x=list(range(1, len(df_top) + 1)),
        y=df_top['ValorTotal'],
        marker_color=cores,
        marker_line_color=COLORS['secondary'],
        marker_line_width=1,
        text=[f'R$ {v/1000:,.0f}k' for v in df_top['ValorTotal']],
        textposition='outside',
        textfont=dict(color='white', size=10),
        hovertemplate='<b>%{customdata}</b><br>R$ %{y:,.2f}<extra></extra>',
        customdata=df_top[VENDAS_COL_SETOR]
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=30, b=20, l=20, r=20),
        height=280,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color='white', size=11),
            tickvals=list(range(1, len(df_top) + 1)),
            ticktext=[f'#{i}' for i in range(1, len(df_top) + 1)],
            title=None
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickfont=dict(color='white'),
            title=None,
            tickformat=',.0f'
        ),
        showlegend=False,
        bargap=0.3
    )

    return fig, df_top


def criar_grafico_evolucao_ciclos(df_setor_ciclo):
    """Cria grafico de linha para evolucao por ciclo."""
    df_ciclo = df_setor_ciclo.groupby(VENDAS_COL_CICLO).agg({
        'ClientesAtivos': 'sum',
        'ClientesMultimarcas': 'sum',
        'ValorTotal': 'sum'
    }).reset_index()

    df_ciclo = df_ciclo.sort_values(VENDAS_COL_CICLO)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df_ciclo[VENDAS_COL_CICLO].astype(str),
            y=df_ciclo['ClientesAtivos'],
            name='Clientes Ativos',
            marker_color=COLORS['primary'],
            opacity=0.7
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=df_ciclo[VENDAS_COL_CICLO].astype(str),
            y=df_ciclo['ValorTotal'],
            name='Valor Total',
            line=dict(color=COLORS['success'], width=3),
            mode='lines+markers',
            marker=dict(size=8)
        ),
        secondary_y=True
    )

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=30, b=20, l=20, r=20),
        height=350,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='white')
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color='white'),
            title=None
        )
    )

    fig.update_yaxes(
        title_text="Clientes",
        secondary_y=False,
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        tickfont=dict(color='white'),
        title_font=dict(color='white')
    )

    fig.update_yaxes(
        title_text="Valor (R$)",
        secondary_y=True,
        showgrid=False,
        tickfont=dict(color=COLORS['success']),
        title_font=dict(color=COLORS['success'])
    )

    return fig


def criar_grafico_marcas(df_vendas_filtrado):
    """Cria grafico de distribuicao por marca."""
    df_marcas = df_vendas_filtrado.groupby(COL_MARCA_BD).agg({
        'QuantidadeItens': 'sum',
        'ValorPraticado': 'sum'
    }).reset_index()

    df_marcas = df_marcas[df_marcas[COL_MARCA_BD] != MARCA_DESCONHECIDA]
    df_marcas = df_marcas.sort_values('ValorPraticado', ascending=False)

    fig = go.Figure(data=[go.Pie(
        labels=df_marcas[COL_MARCA_BD],
        values=df_marcas['ValorPraticado'],
        marker_colors=CHART_COLORS[:len(df_marcas)],
        textinfo='label+percent',
        textfont_size=12,
        textfont_color='white',
        hole=0.4
    )])

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20),
        height=350,
        showlegend=False
    )

    return fig


# =============================================================================
# COMPONENTES DE UI
# =============================================================================
def render_metric_card(label, value, icon="📊"):
    """Renderiza um card de metrica customizado."""
    st.markdown(f"""
        <div class="metric-container">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
            <p class="metric-value">{value}</p>
            <p class="metric-label">{label}</p>
        </div>
    """, unsafe_allow_html=True)


def render_status_badge(text, status="success"):
    """Renderiza um badge de status."""
    return f'<span class="status-badge status-{status}">{text}</span>'


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
def main():
    # Header
    st.markdown('<h1 class="main-title">📊 Multimarks Active Circles</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Analise de Revendedores Ativos e Multimarcas por Ciclo</p>', unsafe_allow_html=True)

    # Carregar BD Produtos
    try:
        df_bd, avisos_bd = carregar_bd_produtos_cached()
        bd_carregado = True
    except DataValidationError as e:
        st.error(f"❌ Erro ao carregar BD Produtos: {str(e)}")
        bd_carregado = False
        df_bd = None
        avisos_bd = []

    # Carregar BD IAF
    try:
        df_bd_iaf, avisos_iaf = carregar_bd_iaf_cached()
        iaf_carregado = True
    except DataValidationError as e:
        st.warning(f"⚠️ BD IAF nao carregado: {str(e)}")
        iaf_carregado = False
        df_bd_iaf = None
        avisos_iaf = []

    # Sidebar
    with st.sidebar:
        st.markdown("### 📁 Upload de Dados")

        # Status do BD
        if bd_carregado:
            st.markdown(f"""
                <div class="info-card">
                    <strong>✅ BD Produtos Carregado</strong><br>
                    <span style="color: {COLORS['primary']}; font-size: 1.5rem; font-weight: bold;">{len(df_bd):,}</span>
                    <span style="color: {COLORS['muted']};"> produtos</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error("❌ BD Produtos nao carregado")

        st.markdown("---")

        # Upload
        arquivo_vendas = st.file_uploader(
            "📤 Planilha de Vendas",
            type=['xlsx', 'xls', 'csv'],
            key='vendas',
            help="Arraste ou clique para fazer upload"
        )

        st.markdown("---")

        # Botao processar
        col1, col2 = st.columns([1, 1])
        with col1:
            processar = st.button(
                "⚡ Processar",
                type="primary",
                use_container_width=True,
                disabled=(not bd_carregado or arquivo_vendas is None)
            )
        with col2:
            if st.button("🔄 Limpar", use_container_width=True):
                if 'dados_processados' in st.session_state:
                    del st.session_state['dados_processados']
                st.rerun()

    # Verificacoes
    if not bd_carregado:
        st.error("O arquivo BD Produtos nao foi encontrado. Verifique `data/bd_produtos.csv`.")
        return

    if arquivo_vendas is None:
        # Tela inicial
        st.markdown("---")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
                <div style="text-align: center; padding: 3rem;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📤</div>
                    <h3 style="color: #FAFAFA;">Faca upload da planilha de Vendas</h3>
                    <p style="color: #A0A0A0;">Arraste o arquivo ou clique no botao na barra lateral</p>
                </div>
            """, unsafe_allow_html=True)

            with st.expander("📋 Formato esperado da planilha", expanded=False):
                st.markdown("""
                    | Coluna | Descricao |
                    |--------|-----------|
                    | Setor | Regiao/Setor |
                    | NomeRevendedora | Nome do cliente |
                    | CodigoRevendedora | Codigo unico |
                    | CicloFaturamento | Ciclo (ex: 202401) |
                    | CodigoProduto | SKU do produto |
                    | NomeProduto | Nome do produto |
                    | Tipo | "Venda" para vendas |
                    | QuantidadeItens | Quantidade |
                    | ValorPraticado | Valor em R$ |
                """)
        return

    # Processamento
    if processar or 'dados_processados' in st.session_state:
        if processar:
            with st.spinner("⏳ Processando dados..."):
                try:
                    vendas_bytes = arquivo_vendas.getvalue()
                    
                    # Verificar se é CSV e capturar relatório de correção
                    csv_fix_report = None
                    csv_fixed_bytes = None
                    if arquivo_vendas.name.lower().endswith('.csv'):
                        from src.io import ler_arquivo
                        vendas_buffer = BytesIO(vendas_bytes)
                        _, csv_fix_report, csv_fixed_bytes = ler_arquivo(vendas_buffer, arquivo_vendas.name, return_report=True)
                        vendas_buffer.seek(0)  # Reset para processar_vendas usar
                    
                    dados = processar_vendas_cached(vendas_bytes, arquivo_vendas.name, df_bd)
                    dados['avisos'] = [f"[BD] {a}" for a in avisos_bd] + dados['avisos']
                    dados['df_bd'] = df_bd
                    dados['csv_fix_report'] = csv_fix_report
                    dados['csv_fixed_bytes'] = csv_fixed_bytes
                    st.session_state['dados_processados'] = dados
                    st.success("✅ Dados processados com sucesso!")
                    
                    # Mostrar aviso de correção CSV se houver
                    if csv_fix_report and csv_fix_report.get('stats', {}).get('joined_broken_records', 0) + csv_fix_report.get('stats', {}).get('fixed_extra_cols', 0) + csv_fix_report.get('stats', {}).get('fixed_missing_cols', 0) > 0:
                        stats = csv_fix_report['stats']
                        joined = stats.get('joined_broken_records', 0)
                        extra = stats.get('fixed_extra_cols', 0)
                        missing = stats.get('fixed_missing_cols', 0)
                        total_fixes = joined + extra + missing
                        
                        st.warning(
                            f"📝 CSV corrigido automaticamente: {joined} registros reconstruídos, "
                            f"{extra + missing} linhas ajustadas. Baixe o relatório para auditoria."
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "📥 Baixar CSV Corrigido",
                                data=csv_fixed_bytes,
                                file_name=arquivo_vendas.name.replace('.csv', '_corrigido.csv'),
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col2:
                            import json
                            report_json = json.dumps(csv_fix_report, ensure_ascii=False, indent=2)
                            st.download_button(
                                "📥 Baixar Relatório JSON",
                                data=report_json.encode('utf-8'),
                                file_name=arquivo_vendas.name.replace('.csv', '_relatorio_correcao.json'),
                                mime="application/json",
                                use_container_width=True
                            )
                    elif csv_fix_report:
                        st.info("✅ CSV validado sem ajustes.")
                        
                except DataValidationError as e:
                    st.error(f"❌ Erro de validacao: {str(e)}")
                    return
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
                    return

        if 'dados_processados' not in st.session_state:
            st.info("👆 Clique em 'Processar' para iniciar a analise.")
            return

        dados = st.session_state['dados_processados']

        # Filtros na sidebar
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🔍 Filtros")

            ciclos_disponiveis = sorted(dados['df_vendas_filtrado'][VENDAS_COL_CICLO].dropna().unique().tolist())
            setores_disponiveis = sorted(dados['df_vendas_filtrado'][VENDAS_COL_SETOR].dropna().unique().tolist())
            marcas_disponiveis = sorted([
                m for m in dados['df_vendas_filtrado'][COL_MARCA_BD].dropna().unique().tolist()
                if m != MARCA_DESCONHECIDA
            ])

            ciclos_selecionados = st.multiselect(
                "📅 Ciclos",
                options=ciclos_disponiveis,
                default=ciclos_disponiveis
            )

            setores_selecionados = st.multiselect(
                "📍 Setores",
                options=setores_disponiveis,
                default=[]
            )

            marcas_selecionadas = st.multiselect(
                "🏷️ Marcas",
                options=marcas_disponiveis,
                default=[]
            )

            apenas_multimarcas = st.checkbox("⭐ Somente Multimarcas", value=False)

        # Aplicar filtros
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

        # Calcular metricas
        metricas = calcular_metricas_gerais(df_clientes_filtrado, df_vendas_filtrado)

        # Avisos
        if dados['avisos']:
            with st.expander("ℹ️ Avisos do processamento", expanded=False):
                for aviso in dados['avisos']:
                    if 'ALERTA' in aviso:
                        st.warning(aviso)
                    else:
                        st.info(aviso)

        st.markdown("---")

        # ==========================================================================
        # METRICAS PRINCIPAIS
        # ==========================================================================
        st.markdown("### 📈 Metricas Principais")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            render_metric_card("Clientes Ativos", f"{metricas['total_ativos']:,}", "👥")
        with col2:
            render_metric_card("Multimarcas", f"{metricas['total_multimarcas']:,}", "⭐")
        with col3:
            render_metric_card("% Multimarcas", f"{metricas['percent_multimarcas']:.1f}%", "📊")
        with col4:
            render_metric_card("Total Itens", f"{metricas['total_itens']:,.0f}", "📦")
        with col5:
            render_metric_card("Valor Total", f"R$ {metricas['total_valor']:,.0f}", "💰")

        st.markdown("---")

        # ==========================================================================
        # TABS PRINCIPAIS
        # ==========================================================================
        tab_visao, tab_multi, tab_novos, tab_audit, tab_cliente, tab_iaf = st.tabs([
            "📊 Visao Geral",
            "⭐ Multimarcas",
            "🆕 Produtos Novos",
            "🔍 Auditoria",
            "👤 Cliente",
            "🏆 IAF"
        ])

        # TAB: VISAO GERAL
        with tab_visao:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🎯 Distribuicao Multimarcas")
                fig_pizza = criar_grafico_pizza_multimarcas(
                    metricas['total_ativos'],
                    metricas['total_multimarcas']
                )
                st.plotly_chart(fig_pizza, use_container_width=True)

            with col2:
                st.markdown("#### 🏷️ Vendas por Marca")
                fig_marcas = criar_grafico_marcas(df_vendas_filtrado)
                st.plotly_chart(fig_marcas, use_container_width=True)

            st.markdown("---")

            st.markdown("#### 📈 Evolucao por Ciclo")
            fig_evolucao = criar_grafico_evolucao_ciclos(df_setor_ciclo_filtrado)
            st.plotly_chart(fig_evolucao, use_container_width=True)

            st.markdown("---")

            # Top 10 Setores com grafico e tabela
            st.markdown("#### 🏆 Top 10 Setores por Valor")
            if not df_setor_ciclo_filtrado.empty:
                fig_setores, df_top_setores = criar_grafico_barras_setores(df_setor_ciclo_filtrado)

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.plotly_chart(fig_setores, use_container_width=True)

                with col2:
                    # Criar tabela rankeada
                    df_tabela = df_top_setores.copy()
                    df_tabela['Rank'] = range(1, len(df_tabela) + 1)
                    df_tabela['Valor'] = df_tabela['ValorTotal'].apply(
                        lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    )
                    df_tabela['Clientes'] = df_tabela['ClientesAtivos'].astype(int)
                    df_tabela = df_tabela[['Rank', VENDAS_COL_SETOR, 'Clientes', 'Valor']]
                    df_tabela.columns = ['#', 'Setor', 'Clientes', 'Valor Total']
                    st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=320)

            st.markdown("---")

            # Resumo por Ciclo
            st.markdown("#### 📋 Resumo por Ciclo")
            if not df_setor_ciclo_filtrado.empty:
                df_ciclo = calcular_estatisticas_ciclo(df_setor_ciclo_filtrado)
                st.dataframe(df_ciclo, use_container_width=True, hide_index=True)

            st.markdown("---")

            st.markdown("#### 📊 Dados por Setor e Ciclo")
            if not df_setor_ciclo_filtrado.empty:
                df_setor_fmt = formatar_tabela_setor_ciclo(df_setor_ciclo_filtrado)
                st.dataframe(df_setor_fmt, use_container_width=True, hide_index=True)

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.download_button(
                        "📥 CSV",
                        data=exportar_csv(df_setor_fmt),
                        file_name=gerar_nome_arquivo("ativos_setor_ciclo", "csv"),
                        mime="text/csv"
                    )
                with col2:
                    st.download_button(
                        "📥 Excel",
                        data=exportar_excel(df_setor_fmt, "Ativos"),
                        file_name=gerar_nome_arquivo("ativos_setor_ciclo", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        # TAB: MULTIMARCAS
        with tab_multi:
            df_multi = df_clientes_filtrado[df_clientes_filtrado[COL_IS_MULTIMARCAS] == True]

            if not df_multi.empty:
                st.markdown(f"#### ⭐ Total: **{len(df_multi):,}** clientes multimarcas")

                df_multi_fmt = formatar_tabela_multimarcas(df_multi)
                st.dataframe(df_multi_fmt, use_container_width=True, hide_index=True)

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.download_button(
                        "📥 CSV",
                        data=exportar_csv(df_multi_fmt),
                        file_name=gerar_nome_arquivo("clientes_multimarcas", "csv"),
                        mime="text/csv",
                        key="dl_multi_csv"
                    )
                with col2:
                    st.download_button(
                        "📥 Excel",
                        data=exportar_excel(df_multi_fmt, "Multimarcas"),
                        file_name=gerar_nome_arquivo("clientes_multimarcas", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_multi_xlsx"
                    )

                st.markdown("---")
                st.markdown("#### 🔗 Combinacoes de Marcas mais Frequentes")
                combinacoes = df_multi_fmt['Marcas'].value_counts().head(10).reset_index()
                combinacoes.columns = ['Combinacao de Marcas', 'Quantidade']
                st.dataframe(combinacoes, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum cliente multimarcas encontrado para os filtros selecionados.")

        # TAB: PRODUTOS NOVOS
        with tab_novos:
            st.markdown("#### 🆕 Produtos Nao Cadastrados no BD")
            st.markdown("Produtos que aparecem nas vendas mas nao estao no cadastro (possiveis lancamentos).")

            df_nao_cadastrados = gerar_produtos_nao_cadastrados(dados['df_vendas_enriquecido'])

            if ciclos_selecionados and not df_nao_cadastrados.empty:
                mask = df_nao_cadastrados['Ciclos'].apply(
                    lambda x: any(c in x for c in [str(c) for c in ciclos_selecionados])
                )
                df_nao_cadastrados = df_nao_cadastrados[mask]

            if not df_nao_cadastrados.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    render_metric_card("Produtos", f"{len(df_nao_cadastrados):,}", "📦")
                with col2:
                    render_metric_card("Itens Vendidos", f"{df_nao_cadastrados['Total_Itens'].sum():,.0f}", "🛒")
                with col3:
                    render_metric_card("Valor", f"R$ {df_nao_cadastrados['Valor_Total'].sum():,.0f}", "💰")

                st.markdown("---")

                df_novos_fmt = df_nao_cadastrados.copy()
                df_novos_fmt['Valor_Total'] = df_novos_fmt['Valor_Total'].apply(lambda x: f"R$ {x:,.2f}")
                df_novos_fmt.columns = ['SKU', 'Nome do Produto', 'Qtde Vendas', 'Total Itens', 'Valor Total', 'Ciclos', 'Setores']

                st.dataframe(df_novos_fmt, use_container_width=True, hide_index=True)

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    df_download = df_nao_cadastrados.copy()
                    df_download.columns = ['SKU', 'Nome_Produto', 'Qtde_Vendas', 'Total_Itens', 'Valor_Total', 'Ciclos', 'Setores']
                    st.download_button(
                        "📥 CSV",
                        data=exportar_csv(df_download),
                        file_name=gerar_nome_arquivo("produtos_nao_cadastrados", "csv"),
                        mime="text/csv",
                        key="dl_novos_csv"
                    )
                with col2:
                    st.download_button(
                        "📥 Excel",
                        data=exportar_excel(df_download, "ProdutosNovos"),
                        file_name=gerar_nome_arquivo("produtos_nao_cadastrados", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_novos_xlsx"
                    )
            else:
                st.success("✅ Todos os produtos vendidos estao cadastrados no BD!")

        # TAB: AUDITORIA
        with tab_audit:
            st.markdown("#### 🔍 Auditoria de SKUs")

            df_audit = dados['df_auditoria'].copy()
            if ciclos_selecionados:
                df_audit = df_audit[df_audit[VENDAS_COL_CICLO].isin(ciclos_selecionados)]

            if not df_audit.empty:
                nao_encontrados = len(df_audit[df_audit['Motivo'] == 'NAO_ENCONTRADO'])
                match_zero = len(df_audit[df_audit['Motivo'] == 'MATCH_COM_ZERO'])

                col1, col2 = st.columns(2)
                with col1:
                    render_metric_card("Nao Encontrados", f"{nao_encontrados:,}", "❌")
                with col2:
                    render_metric_card("Match com Zero", f"{match_zero:,}", "🔄")

                st.markdown("---")

                df_audit_fmt = formatar_tabela_auditoria(df_audit)
                st.dataframe(df_audit_fmt, use_container_width=True, hide_index=True)

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.download_button(
                        "📥 CSV",
                        data=exportar_csv(df_audit_fmt),
                        file_name=gerar_nome_arquivo("auditoria_skus", "csv"),
                        mime="text/csv",
                        key="dl_audit_csv"
                    )
                with col2:
                    st.download_button(
                        "📥 Excel",
                        data=exportar_excel(df_audit_fmt, "Auditoria"),
                        file_name=gerar_nome_arquivo("auditoria_skus", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_audit_xlsx"
                    )
            else:
                st.success("✅ Todos os SKUs foram encontrados no BD!")

        # TAB: CLIENTE
        with tab_cliente:
            st.markdown("#### 👤 Detalhamento por Cliente")

            lista_clientes = gerar_lista_clientes_para_selecao(df_clientes_filtrado)

            if lista_clientes:
                opcoes = {c['label']: c['id'] for c in lista_clientes}
                opcoes_lista = list(opcoes.keys())

                # Inicializar estado se nao existir
                if 'cliente_selecionado_idx' not in st.session_state:
                    st.session_state.cliente_selecionado_idx = 0

                # Garantir que o indice esta dentro do range
                if st.session_state.cliente_selecionado_idx >= len(opcoes_lista):
                    st.session_state.cliente_selecionado_idx = 0

                cliente_selecionado_label = st.selectbox(
                    "🔍 Selecione um cliente",
                    options=opcoes_lista,
                    index=st.session_state.cliente_selecionado_idx,
                    key="select_cliente"
                )

                # Atualizar o indice no estado
                if cliente_selecionado_label in opcoes_lista:
                    st.session_state.cliente_selecionado_idx = opcoes_lista.index(cliente_selecionado_label)

                if cliente_selecionado_label:
                    cliente_id = opcoes[cliente_selecionado_label]

                    df_detalhe, resumo = obter_detalhe_cliente(
                        dados['df_vendas_enriquecido'],
                        cliente_id,
                        ciclo=ciclos_selecionados[0] if len(ciclos_selecionados) == 1 else None
                    )

                    st.markdown("---")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric_card("Marcas", f"{resumo['marcas_distintas']}", "🏷️")
                    with col2:
                        render_metric_card("Itens", f"{resumo['total_itens']:,.0f}", "📦")
                    with col3:
                        render_metric_card("Valor", f"R$ {resumo['total_valor']:,.0f}", "💰")
                    with col4:
                        render_metric_card("Ciclos", f"{len(resumo['ciclos'])}", "📅")

                    if resumo['marcas_lista']:
                        marcas_str = ", ".join([m for m in resumo['marcas_lista'] if m != MARCA_DESCONHECIDA])
                        st.markdown(f"""
                            <div class="info-card">
                                <strong>🏷️ Marcas compradas:</strong> {marcas_str}
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("#### 📋 Itens Comprados")

                    if not df_detalhe.empty:
                        st.dataframe(df_detalhe, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum item encontrado.")
            else:
                st.info("Nenhum cliente encontrado para os filtros selecionados.")

        # TAB: IAF
        with tab_iaf:
            st.markdown("#### 🏆 Vendas de Itens IAF (Premiacao)")

            if not iaf_carregado:
                st.warning("⚠️ BD IAF nao carregado. Verifique o arquivo `data/iaf_2026.xlsx`.")
            else:
                st.markdown(f"Base IAF com **{len(df_bd_iaf):,}** produtos carregados.")

                # Cruzar vendas com IAF
                df_iaf = cruzar_vendas_com_iaf(dados['df_vendas_enriquecido'], df_bd_iaf)

                # Aplicar filtros de ciclo e setor
                if ciclos_selecionados and not df_iaf.empty:
                    df_iaf = df_iaf[df_iaf[VENDAS_COL_CICLO].isin(ciclos_selecionados)]
                if setores_selecionados and not df_iaf.empty:
                    df_iaf = df_iaf[df_iaf[VENDAS_COL_SETOR].isin(setores_selecionados)]

                if not df_iaf.empty:
                    # Metricas
                    total_itens_iaf = df_iaf['QuantidadeItens'].sum()
                    total_valor_iaf = df_iaf['ValorPraticado'].sum()
                    total_clientes_iaf = df_iaf['CodigoRevendedora'].nunique()
                    total_skus_iaf = df_iaf['SKU'].nunique()

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric_card("Clientes", f"{total_clientes_iaf:,}", "👥")
                    with col2:
                        render_metric_card("SKUs IAF", f"{total_skus_iaf:,}", "📦")
                    with col3:
                        render_metric_card("Itens", f"{total_itens_iaf:,.0f}", "🛒")
                    with col4:
                        render_metric_card("Valor", f"R$ {total_valor_iaf:,.0f}", "💰")

                    st.markdown("---")

                    # Tabela de vendas IAF
                    df_iaf_fmt = formatar_tabela_iaf(df_iaf)
                    st.dataframe(df_iaf_fmt, use_container_width=True, hide_index=True)

                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        st.download_button(
                            "📥 CSV",
                            data=exportar_csv(df_iaf_fmt),
                            file_name=gerar_nome_arquivo("vendas_iaf", "csv"),
                            mime="text/csv",
                            key="dl_iaf_csv"
                        )
                    with col2:
                        st.download_button(
                            "📥 Excel",
                            data=exportar_excel(df_iaf_fmt, "VendasIAF"),
                            file_name=gerar_nome_arquivo("vendas_iaf", "xlsx"),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_iaf_xlsx"
                        )

                    st.markdown("---")

                    # Top produtos IAF
                    st.markdown("#### 📊 Top Produtos IAF mais Vendidos")
                    df_top_iaf = df_iaf.groupby(['SKU', 'Nome_IAF', 'Marca_IAF']).agg({
                        'QuantidadeItens': 'sum',
                        'ValorPraticado': 'sum'
                    }).reset_index().sort_values('ValorPraticado', ascending=False).head(15)

                    df_top_iaf['ValorPraticado'] = df_top_iaf['ValorPraticado'].apply(
                        lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    )
                    df_top_iaf.columns = ['SKU', 'Produto', 'Marca', 'Quantidade', 'Valor Total']
                    st.dataframe(df_top_iaf, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma venda de itens IAF encontrada para os filtros selecionados.")


# =============================================================================
# EXECUCAO
# =============================================================================
if __name__ == "__main__":
    main()
