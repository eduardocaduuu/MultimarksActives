# Multimarks Active Circles

Aplicacao para analise de revendedores ativos e multimarcas por ciclo de faturamento.

## Funcionalidades

- **Analise de Clientes Ativos**: Identifica clientes que realizaram ao menos uma compra por ciclo
- **Identificacao de Multimarcas**: Detecta clientes que compram de mais de uma marca no mesmo ciclo
- **Visao por Setor e Ciclo**: Agregacoes detalhadas por setor e periodo
- **Auditoria de SKUs**: Rastreamento de produtos nao encontrados no cadastro
- **Exportacao de Dados**: CSV e Excel para todas as tabelas

## Requisitos

- Python 3.9+
- Dependencias listadas em `requirements.txt`

## Instalacao Local

```bash
# Clonar o repositorio
git clone https://github.com/eduardocaduuu/MultimarksActives.git
cd MultimarksActives

# Criar ambiente virtual (opcional mas recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Executar a aplicacao
streamlit run app.py
```

## Formato das Planilhas

### BD Produtos (Cadastro de Produtos)

Planilha com o catalogo de produtos e suas marcas.

| Coluna | Descricao | Exemplo |
|--------|-----------|---------|
| SKU | Codigo do produto (4-5 digitos) | 01234 |
| Nome | Nome do produto | Perfume Florata |
| Marca | Marca do produto | oBoticario |

**Marcas esperadas**: oBoticario, Eudora, AuAmigos, Quem Disse Berenice (QDB), O.U.I

### Planilha de Vendas

Planilha com as transacoes de venda.

| Coluna | Descricao | Obrigatoria |
|--------|-----------|-------------|
| Setor | Setor/Regiao da venda | Sim |
| NomeRevendedora | Nome do revendedor | Sim |
| CodigoRevendedora | Codigo unico do revendedor | Sim |
| CicloFaturamento | Ciclo de faturamento (ex: 202401) | Sim |
| CodigoProduto | SKU do produto | Sim |
| NomeProduto | Nome do produto na venda | Sim |
| Tipo | Tipo da transacao (Venda, Devolucao, etc) | Sim |
| QuantidadeItens | Quantidade vendida | Sim |
| ValorPraticado | Valor total da linha | Sim |
| MeioCaptacao | Canal de venda | Nao |

**Importante**: Apenas linhas com `Tipo = "Venda"` sao consideradas nos calculos.

## Dados de Teste

Use os dados abaixo para testar a aplicacao:

### BD_Produtos_Teste.csv

```csv
SKU,Nome,Marca
01234,Perfume Florata,oBoticario
05678,Batom Intense,Eudora
1234,Colonia Malbec,oBoticario
09876,Creme Hidratante,Quem Disse Berenice
00123,Shampoo Pet,AuAmigos
```

### Vendas_Teste.csv

```csv
Setor,NomeRevendedora,CodigoRevendedora,CicloFaturamento,CodigoProduto,NomeProduto,Tipo,QuantidadeItens,ValorPraticado,MeioCaptacao
Norte,Maria Silva,R001,202401,01234,Perfume Florata,Venda,2,179.80,Digital
Norte,Maria Silva,R001,202401,05678,Batom Intense,Venda,1,45.90,Digital
Sul,Joao Santos,R002,202401,1234,Colonia Malbec,Venda,1,289.90,Presencial
Sul,Joao Santos,R002,202401,01234,Perfume Florata,Venda,1,89.90,Presencial
Centro,Ana Costa,R003,202401,09876,Creme Hidratante,Venda,3,120.00,Digital
Centro,Ana Costa,R003,202401,99999,Produto Desconhecido,Venda,1,50.00,Digital
Norte,Maria Silva,R001,202402,00123,Shampoo Pet,Venda,2,80.00,Digital
Norte,Maria Silva,R001,202402,05678,Batom Intense,Venda,1,45.90,Digital
```

### Resultados Esperados

Com os dados de teste acima:

- **Maria Silva (R001)**: Multimarcas no ciclo 202401 (oBoticario + Eudora) e 202402 (AuAmigos + Eudora)
- **Joao Santos (R002)**: NAO multimarcas (apenas oBoticario)
- **Ana Costa (R003)**: NAO multimarcas (apenas Quem Disse Berenice) + 1 SKU nao encontrado (99999)
- **Match com zero a esquerda**: SKU 1234 deve casar com 01234 do BD

## Deploy no Render

O projeto esta configurado para deploy no Render (plano gratuito).

### Configuracao

1. Conecte o repositorio no Render
2. Selecione "Web Service"
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port=$PORT --server.headless=true`

Ou use o arquivo `render.yaml` incluido no projeto.

## Estrutura do Projeto

```
MultimarksActiveCircles/
├── app.py              # Interface principal Streamlit
├── requirements.txt    # Dependencias Python
├── render.yaml         # Configuracao do Render
├── README.md           # Este arquivo
└── src/
    ├── __init__.py     # Exports do modulo
    ├── constants.py    # Constantes e configuracoes
    ├── io.py           # Leitura e validacao de dados
    ├── transform.py    # Transformacoes e metricas
    ├── reports.py      # Geracao de relatorios
    └── export.py       # Exportacao de dados
```

## Regras de Negocio

### Normalizacao de SKU

1. Converter para string
2. Remover espacos e caracteres nao numericos
3. Preservar zeros a esquerda
4. Match robusto: primeiro exato, depois com zero a esquerda para codigos de 4 digitos

### Cliente Ativo

Cliente com ao menos 1 linha de Tipo="Venda" no ciclo de faturamento.

### Cliente Multimarcas

Cliente que comprou produtos de 2 ou mais marcas DISTINTAS no mesmo ciclo.
(Marcas "DESCONHECIDA" nao contam)

### Identificacao do Cliente

- Chave primaria: CodigoRevendedora
- Fallback: NomeRevendedora + Setor (se codigo estiver vazio)

## Licenca

MIT License
