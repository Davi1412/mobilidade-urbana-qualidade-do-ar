# Mobilidade Urbana e Qualidade do Ar — ODS 11

O projeto tem como tema o Objetivo de Desenvolvimento Sustentável (ODS) 11 da ONU — Cidades e Comunidades Sustentáveis — com recorte em Mobilidade Urbana e Qualidade do Ar, combinando um dashboard analítico com um assistente de Inteligência Artificial executado localmente (sem uso de APIs pagas de IA).

## Visão geral

A aplicação cruza posições de ônibus da API SPTrans Olho Vivo com medições horárias de qualidade do ar da CETESB. O dashboard permite comparar a Zona Leste e o Centro de São Paulo, analisar fluxo de veículos, linhas, distâncias até estações ambientais e concentrações de MP10, MP2.5, NO e NO2.

O assistente de IA usa modelos locais disponibilizados pelo Ollama. Somente indicadores agregados são enviados ao modelo local; não há dependência de uma API paga de IA.

## Tecnologias

- Python e Streamlit
- PostgreSQL com PostGIS
- Pandas, Plotly, Folium e Streamlit Folium
- API SPTrans Olho Vivo
- Dados de qualidade do ar da CETESB/QUALAR
- Ollama para execução local do modelo de linguagem

## Estrutura

```text
.
├── app.py                       # Dashboard principal
├── components/                  # Componentes da interface
├── pages/                       # Mapa, qualidade do ar e assistente de IA
├── services/                    # Consultas, gráficos, mapas e integração Ollama
├── scripts/                     # Coleta e importação de dados
├── dados_brutos/                # Arquivos de origem utilizados no estudo
├── database/schema.sql          # Estrutura do PostgreSQL/PostGIS
├── db.py                        # Conexão com o banco
└── requirements.txt
```

## Configuração

### 1. Pré-requisitos

- Python 3.12 ou superior
- PostgreSQL com extensão PostGIS
- Ollama instalado, caso queira utilizar o assistente de IA
- Token da API SPTrans Olho Vivo, necessário apenas para novas coletas

### 2. Ambiente Python

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 3. Variáveis de ambiente

Copie `.env.example` para `.env` e informe as credenciais locais:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=weather_report
DB_USER=postgres
DB_PASSWORD=sua_senha
OLHOVIVO_TOKEN=seu_token
```

O arquivo `.env` é ignorado pelo Git e não deve ser versionado.

### 4. Banco de dados

Crie o banco, habilite o PostGIS e aplique o esquema:

```sql
CREATE DATABASE weather_report;
```

No banco criado:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Em seguida, execute `database/schema.sql` pelo pgAdmin ou `psql`.

### 5. Importação e coleta

Cadastrar as linhas monitoradas:

```bash
python -m scripts.cadastrar_linhas
```

Coletar posições para uma janela configurada:

```bash
python -m scripts.coletar_posicoes meio_dia
```

Importar os relatórios da CETESB:

```bash
python -m scripts.importar_cetesb_novo
```

O importador reconhece os relatórios matriciais exportados pelo QUALAR, ignora medições vazias e converte o horário `24:00` para `00:00` do dia seguinte.

### 6. Assistente local

Instale um modelo pelo Ollama, por exemplo:

```bash
ollama pull llama3.2:3b
```

Mantenha o Ollama em execução. A aplicação consulta os modelos disponíveis em `http://localhost:11434` e permite selecionar um deles na interface.

### 7. Execução

```bash
streamlit run app.py
```

## Dados analisados

- Regiões: Zona Leste e Centro
- Estações CETESB: Itaim Paulista e Cerqueira César
- Poluentes: MP10, MP2.5, NO e NO2
- Mobilidade: linhas, veículos, posições, janelas de coleta e distância até a estação ambiental mais próxima

## Observações

- Os dados refletem as datas e janelas presentes nos arquivos versionados.
- A disponibilidade das medições depende da correspondência entre estação, data e hora das posições dos ônibus.
- Credenciais do PostgreSQL e o token da SPTrans não estão incluídos no repositório.
- O assistente produz análises auxiliares e suas respostas devem ser revisadas pelo usuário.
