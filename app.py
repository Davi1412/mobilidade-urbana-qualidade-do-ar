from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from components.sidebar import exibir_sidebar_global
from services.consultas import (
    buscar_distribuicao_distancias,
    buscar_fluxo_linhas,
    buscar_insights_dashboard,
    buscar_kpis,
    buscar_resumo_regioes,
)
from services.graficos import (
    grafico_coletas_regiao,
    grafico_distribuicao_distancias,
    grafico_fluxo_linhas,
    grafico_poluentes,
)


# Esta configuração deve aparecer antes dos demais comandos do Streamlit.
# Ela define o título da aba, o ícone, o uso da largura total da página
# e o estado inicial da barra lateral.
st.set_page_config(
    page_title="Weather Report",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)


def formatar_inteiro(valor) -> str:
    """
    Converte um número inteiro para o padrão brasileiro.

    Exemplo:
        12345 -> 12.345
    """

    if pd.isna(valor):
        return "0"

    return f"{int(valor):,}".replace(",", ".")


def formatar_decimal(
    valor,
    casas: int = 2,
    valor_nulo: str = "Indisponível",
) -> str:
    """
    Converte um número decimal para o padrão brasileiro.

    Exemplo:
        7742.96 -> 7.742,96
    """

    if pd.isna(valor):
        return valor_nulo

    texto = f"{float(valor):,.{casas}f}"

    return (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_percentual(valor) -> str:
    """
    Formata um valor numérico acrescentando o símbolo de percentual.
    """

    return f"{formatar_decimal(valor)}%"


def valor_texto(
    valor,
    padrao: str = "Indisponível",
) -> str:
    """
    Converte um valor para texto seguro antes de inseri-lo em HTML.

    O escape é importante porque alguns dados vindos do banco são
    exibidos em cartões construídos com st.markdown.
    """

    if pd.isna(valor):
        return padrao

    return html.escape(str(valor))


def aplicar_estilo() -> None:
    """
    Define os estilos visuais exclusivos da página inicial.

    O CSS personaliza:
    - margens da página;
    - cartões de métricas;
    - cabeçalho;
    - cartões de resumo e insights;
    - etiquetas que mostram os filtros ativos.
    """

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.6rem;
                padding-bottom: 2rem;
            }

            [data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(128, 128, 128, 0.25);
                padding: 1rem;
                border-radius: 0.8rem;
                min-height: 125px;
            }

            [data-testid="stMetricLabel"] {
                font-size: 0.92rem;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.65rem;
            }

            .cabecalho {
                padding: 1.4rem 1.5rem;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 1rem;
                margin-bottom: 1.2rem;
            }

            .cabecalho h1 {
                margin: 0;
                font-size: 2.2rem;
            }

            .cabecalho p {
                margin: 0.4rem 0 0 0;
                opacity: 0.78;
            }

            .cartao-texto {
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 0.9rem;
                padding: 1.1rem 1.2rem;
                height: 100%;
            }

            .cartao-texto h3 {
                margin-top: 0;
                margin-bottom: 0.8rem;
            }

            .cartao-texto p {
                margin: 0.38rem 0;
                line-height: 1.45;
            }

            .filtros-ativos {
                margin: 0.4rem 0 1rem 0;
            }

            .etiqueta-filtro {
                display: inline-block;
                padding: 0.3rem 0.62rem;
                margin: 0.12rem 0.18rem 0.12rem 0;
                border: 1px solid rgba(128, 128, 128, 0.30);
                border-radius: 999px;
                font-size: 0.86rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def exibir_cabecalho() -> None:
    """
    Exibe o título principal e uma breve descrição da aplicação.
    """

    st.markdown(
        """
        <div class="cabecalho">
            <h1>Weather Report</h1>
            <p>
                Monitoramento integrado da mobilidade urbana e da
                qualidade do ar no município de São Paulo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exibir_aviso_assistente_local() -> None:
    """Explica os requisitos opcionais do assistente de IA local."""

    st.info(
        "**Assistente de IA local (recurso opcional):** o dashboard pode "
        "ser utilizado normalmente sem IA. Para usar o assistente, é "
        "necessário instalar o Ollama, manter o serviço em execução e "
        "baixar ao menos um modelo local. Se nenhum modelo for encontrado, "
        "a mensagem de indisponibilidade é esperada e não representa erro "
        "da aplicação."
    )

    with st.expander("Como habilitar o assistente de IA"):
        st.markdown(
            """
            1. Instale o **Ollama** no computador.
            2. Baixe um modelo local, por exemplo:

               ```bash
               ollama pull llama3.2:3b
               ```

            3. Mantenha o Ollama ativo em `http://localhost:11434`.
            4. Abra a página **Assistente IA** e selecione o modelo instalado.

            O processamento é executado localmente e não utiliza APIs pagas
            de Inteligência Artificial.
            """
        )


def resumir_selecao(
    valores,
    rotulo_todos: str,
    limite: int = 3,
) -> str:
    """
    Resume listas longas para evitar etiquetas extensas.

    Exemplo:
        ['A', 'B', 'C', 'D'] -> 'A, B, C e mais 1'
    """

    if not valores:
        return rotulo_todos

    valores_texto = [str(valor) for valor in valores]

    if len(valores_texto) <= limite:
        return ", ".join(valores_texto)

    exibidos = ", ".join(valores_texto[:limite])
    restantes = len(valores_texto) - limite

    return f"{exibidos} e mais {restantes}"


def exibir_filtros_ativos(
    filtros: dict,
) -> None:
    """
    Mostra um resumo do recorte atual do dashboard.

    A sidebar permanece responsável pela seleção dos filtros.
    Esta função apenas informa ao usuário quais filtros estão ativos.
    """

    regioes = resumir_selecao(
        filtros.get("regioes"),
        "Todas",
    )

    linhas = resumir_selecao(
        filtros.get("linhas"),
        "Todas",
    )

    veiculos = resumir_selecao(
        filtros.get("veiculos"),
        "Todos",
    )

    janelas = resumir_selecao(
        filtros.get("janelas"),
        "Todas",
    )

    data_inicial = filtros.get("data_inicial")
    data_final = filtros.get("data_final")

    periodo = "Todo o período disponível"

    if data_inicial and data_final:
        periodo = (
            f"{data_inicial.strftime('%d/%m/%Y')} até "
            f"{data_final.strftime('%d/%m/%Y')}"
        )

    etiquetas = [
        f"Regiões: {regioes}",
        f"Linhas: {linhas}",
        f"Veículos: {veiculos}",
        f"Janelas: {janelas}",
        f"Período: {periodo}",
    ]

    html_etiquetas = "".join(
        (
            '<span class="etiqueta-filtro">'
            f"{html.escape(etiqueta)}"
            "</span>"
        )
        for etiqueta in etiquetas
    )

    st.markdown("#### Filtros ativos")

    st.markdown(
        f'<div class="filtros-ativos">{html_etiquetas}</div>',
        unsafe_allow_html=True,
    )


def exibir_kpis(
    dados_kpis: pd.DataFrame,
) -> None:
    """
    Exibe os indicadores executivos da Home.

    A função espera uma única linha retornada por buscar_kpis().
    """

    if dados_kpis.empty:
        st.warning(
            "Nenhum indicador foi encontrado para os filtros selecionados."
        )
        return

    kpis = dados_kpis.iloc[0]

    primeira_linha = st.columns(6)

    primeira_linha[0].metric(
        "Posições coletadas",
        formatar_inteiro(kpis["total_posicoes"]),
    )

    primeira_linha[1].metric(
        "Veículos",
        formatar_inteiro(kpis["total_veiculos"]),
    )

    primeira_linha[2].metric(
        "Linhas",
        formatar_inteiro(kpis["total_linhas"]),
    )

    primeira_linha[3].metric(
        "Regiões",
        formatar_inteiro(kpis["total_regioes"]),
    )

    primeira_linha[4].metric(
        "Distância média",
        f'{formatar_decimal(kpis["distancia_media"])} m',
    )

    primeira_linha[5].metric(
        "Cobertura ambiental",
        formatar_percentual(
            kpis["cobertura_ambiental_percentual"]
        ),
    )

    segunda_linha = st.columns(5)

    segunda_linha[0].metric(
        "Maior distância",
        f'{formatar_decimal(kpis["maior_distancia"])} m',
    )

    segunda_linha[1].metric(
        "Registros com MP10",
        formatar_inteiro(kpis["registros_com_mp10"]),
    )

    segunda_linha[2].metric(
        "Registros com MP2.5",
        formatar_inteiro(kpis["registros_com_mp25"]),
    )

    segunda_linha[3].metric(
        "Registros com NO",
        formatar_inteiro(kpis["registros_com_no"]),
    )

    segunda_linha[4].metric(
        "Registros com NO2",
        formatar_inteiro(kpis["registros_com_no2"]),
    )


def exibir_resumo_executivo(
    dados_kpis: pd.DataFrame,
) -> None:
    """
    Converte os KPIs em uma explicação textual rápida.

    O texto é determinístico: ele é construído diretamente a partir
    dos valores do banco e ainda não utiliza inteligência artificial.
    """

    if dados_kpis.empty:
        return

    kpis = dados_kpis.iloc[0]

    total_posicoes = formatar_inteiro(
        kpis["total_posicoes"]
    )
    total_veiculos = formatar_inteiro(
        kpis["total_veiculos"]
    )
    total_linhas = formatar_inteiro(
        kpis["total_linhas"]
    )
    total_regioes = formatar_inteiro(
        kpis["total_regioes"]
    )
    distancia_media = formatar_decimal(
        kpis["distancia_media"]
    )
    cobertura = formatar_percentual(
        kpis["cobertura_ambiental_percentual"]
    )

    st.markdown(
        f"""
        <div class="cartao-texto">
            <h3>Resumo executivo</h3>
            <p>
                O recorte selecionado reúne
                <strong>{total_posicoes} posições</strong>,
                provenientes de
                <strong>{total_veiculos} veículos</strong>
                distribuídos em
                <strong>{total_linhas} linhas</strong>
                e <strong>{total_regioes} regiões</strong>.
            </p>
            <p>
                A distância média entre os ônibus e as estações
                ambientais foi de
                <strong>{distancia_media} metros</strong>.
            </p>
            <p>
                A cobertura de dados ambientais alcançou
                <strong>{cobertura}</strong> das coletas analisadas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exibir_insights(
    dados_insights: pd.DataFrame,
) -> None:
    """
    Exibe os principais destaques calculados para o recorte atual.
    """

    if dados_insights.empty:
        st.info(
            "Não há dados suficientes para calcular os insights."
        )
        return

    insights = dados_insights.iloc[0]

    regiao = valor_texto(
        insights["regiao_maior_fluxo"]
    )
    total_regiao = formatar_inteiro(
        insights["total_regiao_maior_fluxo"]
    )

    linha = valor_texto(
        insights["linha_mais_observada"]
    )
    total_linha = formatar_inteiro(
        insights["total_linha_mais_observada"]
    )

    estacao = valor_texto(
        insights["estacao_mais_utilizada"]
    )
    total_estacao = formatar_inteiro(
        insights["total_estacao_mais_utilizada"]
    )

    maior_distancia = formatar_decimal(
        insights["maior_distancia"]
    )
    distancia_media = formatar_decimal(
        insights["distancia_media"]
    )

    st.markdown(
        f"""
        <div class="cartao-texto">
            <h3>Insights automáticos</h3>
            <p>
                <strong>Região com maior fluxo:</strong>
                {regiao} ({total_regiao} coletas)
            </p>
            <p>
                <strong>Linha mais observada:</strong>
                {linha} ({total_linha} coletas)
            </p>
            <p>
                <strong>Estação mais utilizada:</strong>
                {estacao} ({total_estacao} associações)
            </p>
            <p>
                <strong>Maior distância registrada:</strong>
                {maior_distancia} m
            </p>
            <p>
                <strong>Distância média:</strong>
                {distancia_media} m
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preparar_tabela(
    dados: pd.DataFrame,
) -> pd.DataFrame:
    """
    Renomeia e formata as colunas da tabela comparativa.

    A função trabalha sobre uma cópia para não alterar o DataFrame
    original, que também é utilizado pelos gráficos.
    """

    tabela = dados.copy()

    nomes = {
        "regiao": "Região",
        "total_coletas": "Coletas",
        "total_veiculos": "Veículos",
        "total_linhas": "Linhas",
        "distancia_media": "Distância média (m)",
        "mp10": "MP10",
        "mp25": "MP2.5",
        "no": "NO",
        "no2": "NO2",
    }

    tabela = tabela.rename(columns=nomes)

    colunas_decimais = [
        "Distância média (m)",
        "MP10",
        "MP2.5",
        "NO",
        "NO2",
    ]

    for coluna in colunas_decimais:
        if coluna in tabela.columns:
            tabela[coluna] = tabela[coluna].apply(
                formatar_decimal
            )

    return tabela


def main() -> None:
    """
    Controla o fluxo completo da página inicial.

    Ordem de execução:
    1. Aplica o estilo e exibe o cabeçalho.
    2. Informa os requisitos opcionais do assistente de IA local.
    3. Lê os filtros globais da sidebar.
    4. Executa todas as consultas com o mesmo recorte.
    5. Exibe KPIs, resumos, gráficos e tabela.
    6. Mostra detalhes técnicos caso ocorra uma exceção.
    """

    aplicar_estilo()
    exibir_cabecalho()
    exibir_aviso_assistente_local()

    try:
        filtros = exibir_sidebar_global()

        # Todas as consultas recebem exatamente o mesmo dicionário
        # de filtros. Isso garante coerência entre os componentes.
        dados_kpis = buscar_kpis(**filtros)
        resumo_regioes = buscar_resumo_regioes(**filtros)
        fluxo_linhas = buscar_fluxo_linhas(**filtros)

        distribuicao_distancias = (
            buscar_distribuicao_distancias(**filtros)
        )

        dados_insights = buscar_insights_dashboard(
            **filtros
        )

        exibir_filtros_ativos(filtros)

        st.subheader("Indicadores executivos")
        exibir_kpis(dados_kpis)

        st.divider()

        coluna_resumo, coluna_insights = st.columns(2)

        with coluna_resumo:
            exibir_resumo_executivo(dados_kpis)

        with coluna_insights:
            exibir_insights(dados_insights)

        st.divider()
        st.subheader("Mobilidade urbana")

        coluna_regiao, coluna_linha = st.columns(2)

        with coluna_regiao:
            st.plotly_chart(
                grafico_coletas_regiao(
                    resumo_regioes
                ),
                width="stretch",
            )

        with coluna_linha:
            st.plotly_chart(
                grafico_fluxo_linhas(
                    fluxo_linhas
                ),
                width="stretch",
            )

        st.subheader(
            "Integração espacial e qualidade do ar"
        )

        coluna_poluentes, coluna_distancias = st.columns(2)

        with coluna_poluentes:
            st.plotly_chart(
                grafico_poluentes(
                    resumo_regioes
                ),
                width="stretch",
            )

        with coluna_distancias:
            st.plotly_chart(
                grafico_distribuicao_distancias(
                    distribuicao_distancias
                ),
                width="stretch",
            )

        st.subheader("Resumo comparativo por região")

        st.dataframe(
            preparar_tabela(resumo_regioes),
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "Valores nulos indicam ausência de medição disponível "
            "para a estação e o período analisados. A análise é "
            "descritiva e não estabelece relação causal entre "
            "mobilidade urbana e concentração de poluentes."
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar os dados do dashboard."
        )

        # A mensagem principal permanece simples para o usuário.
        # Os detalhes técnicos ficam disponíveis para depuração.
        with st.expander("Detalhes técnicos"):
            st.exception(erro)


if __name__ == "__main__":
    main()
