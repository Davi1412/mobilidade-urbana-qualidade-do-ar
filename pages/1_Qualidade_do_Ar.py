from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from components.sidebar import exibir_sidebar_global
from services.consultas import (
    buscar_cobertura_por_linha,
    buscar_detalhes_qualidade_ar,
    buscar_kpis_qualidade_ar,
    buscar_poluentes_por_distancia,
    buscar_poluentes_por_linha,
)
from services.graficos import (
    grafico_cobertura_ambiental_linha,
    grafico_cobertura_detalhada_linha,
    grafico_cobertura_poluentes,
    grafico_medias_poluentes_linha,
    grafico_poluentes_por_distancia,
)


# Cada página do Streamlit pode possuir sua própria configuração.
# Esta instrução precisa aparecer antes de qualquer outro comando visual.
st.set_page_config(
    page_title="Qualidade do Ar | Weather Report",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def formatar_inteiro(valor) -> str:
    """
    Formata números inteiros no padrão brasileiro.

    Exemplo:
        12500 -> 12.500
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
    Formata números decimais no padrão brasileiro.

    Exemplo:
        42.75 -> 42,75
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
    Formata um valor numérico como percentual.
    """

    if pd.isna(valor):
        return "Indisponível"

    return f"{formatar_decimal(valor)}%"


def aplicar_estilo() -> None:
    """
    Aplica estilos exclusivos da página Qualidade do Ar.

    O CSS complementa os componentes nativos do Streamlit sem alterar
    a lógica dos filtros, consultas ou gráficos.
    """

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }

            [data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(128, 128, 128, 0.25);
                padding: 1rem;
                border-radius: 0.8rem;
                min-height: 122px;
            }

            [data-testid="stMetricLabel"] {
                font-size: 0.91rem;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.58rem;
            }

            .cabecalho-ar {
                padding: 1.35rem 1.5rem;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 1rem;
                margin-bottom: 1rem;
            }

            .cabecalho-ar h1 {
                margin: 0;
                font-size: 2.1rem;
            }

            .cabecalho-ar p {
                margin: 0.45rem 0 0 0;
                opacity: 0.78;
                line-height: 1.5;
            }

            .cartao-interpretacao {
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 0.9rem;
                padding: 1.05rem 1.2rem;
                height: 100%;
            }

            .cartao-interpretacao h3 {
                margin-top: 0;
                margin-bottom: 0.75rem;
            }

            .cartao-interpretacao p {
                margin: 0.42rem 0;
                line-height: 1.5;
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
    Exibe o título e explica o objetivo analítico da página.
    """

    st.markdown(
        """
        <div class="cabecalho-ar">
            <h1>🌫️ Qualidade do Ar e Transporte Público</h1>
            <p>
                Análise das medições de MP10, MP2.5, NO e NO2 associadas
                às posições dos ônibus selecionados. Os resultados
                representam relações espaciais e temporais observadas e
                não demonstram causalidade entre uma linha específica e
                a concentração de poluentes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def resumir_lista(
    valores,
    texto_todos: str,
    limite: int = 3,
) -> str:
    """
    Resume listas longas para que os filtros não ocupem espaço excessivo.
    """

    if not valores:
        return texto_todos

    valores_texto = [str(valor) for valor in valores]

    if len(valores_texto) <= limite:
        return ", ".join(valores_texto)

    primeiros = ", ".join(valores_texto[:limite])
    restantes = len(valores_texto) - limite

    return f"{primeiros} e mais {restantes}"


def exibir_filtros_ativos(filtros: dict) -> None:
    """
    Apresenta o recorte usado por todas as consultas da página.
    """

    data_inicial = filtros.get("data_inicial")
    data_final = filtros.get("data_final")

    periodo = "Todo o período disponível"

    if data_inicial and data_final:
        periodo = (
            f"{data_inicial.strftime('%d/%m/%Y')} até "
            f"{data_final.strftime('%d/%m/%Y')}"
        )

    etiquetas = [
        (
            "Regiões: "
            + resumir_lista(
                filtros.get("regioes"),
                "Todas",
            )
        ),
        (
            "Linhas: "
            + resumir_lista(
                filtros.get("linhas"),
                "Todas",
            )
        ),
        (
            "Veículos: "
            + resumir_lista(
                filtros.get("veiculos"),
                "Todos",
            )
        ),
        (
            "Janelas: "
            + resumir_lista(
                filtros.get("janelas"),
                "Todas",
            )
        ),
        f"Período: {periodo}",
    ]

    etiquetas_html = "".join(
        (
            '<span class="etiqueta-filtro">'
            f"{html.escape(etiqueta)}"
            "</span>"
        )
        for etiqueta in etiquetas
    )

    st.markdown("#### Filtros ativos")
    st.markdown(
        etiquetas_html,
        unsafe_allow_html=True,
    )


def exibir_kpis_ambientais(
    dados_kpis: pd.DataFrame,
) -> None:
    """
    Exibe os principais indicadores ambientais do recorte filtrado.

    A primeira linha apresenta as médias dos quatro poluentes.
    A segunda linha contextualiza volume, estações e cobertura.
    """

    if dados_kpis.empty:
        st.warning(
            "Nenhum indicador ambiental foi encontrado para os filtros."
        )
        return

    kpis = dados_kpis.iloc[0]

    colunas_medias = st.columns(4)

    colunas_medias[0].metric(
        "Média de MP10",
        formatar_decimal(kpis["media_mp10"]),
    )

    colunas_medias[1].metric(
        "Média de MP2.5",
        formatar_decimal(kpis["media_mp25"]),
    )

    colunas_medias[2].metric(
        "Média de NO",
        formatar_decimal(kpis["media_no"]),
    )

    colunas_medias[3].metric(
        "Média de NO2",
        formatar_decimal(kpis["media_no2"]),
    )

    colunas_contexto = st.columns(4)

    colunas_contexto[0].metric(
        "Coletas analisadas",
        formatar_inteiro(kpis["total_coletas"]),
    )

    colunas_contexto[1].metric(
        "Coletas com dados ambientais",
        formatar_inteiro(
            kpis["coletas_com_dados_ambientais"]
        ),
    )

    colunas_contexto[2].metric(
        "Estações associadas",
        formatar_inteiro(kpis["total_estacoes"]),
    )

    colunas_contexto[3].metric(
        "Cobertura ambiental",
        formatar_percentual(
            kpis["cobertura_ambiental_percentual"]
        ),
    )


def exibir_maximos_observados(
    dados_kpis: pd.DataFrame,
) -> None:
    """
    Exibe os maiores valores encontrados no recorte.

    Esses valores são descritivos. Não são comparados automaticamente
    com padrões legais ou limites de saúde, pois essa interpretação
    exige unidade, tempo de exposição e norma aplicável bem definidos.
    """

    if dados_kpis.empty:
        return

    kpis = dados_kpis.iloc[0]

    st.markdown("#### Maiores valores observados")

    colunas = st.columns(4)

    colunas[0].metric(
        "Máximo de MP10",
        formatar_decimal(kpis["maximo_mp10"]),
    )

    colunas[1].metric(
        "Máximo de MP2.5",
        formatar_decimal(kpis["maximo_mp25"]),
    )

    colunas[2].metric(
        "Máximo de NO",
        formatar_decimal(kpis["maximo_no"]),
    )

    colunas[3].metric(
        "Máximo de NO2",
        formatar_decimal(kpis["maximo_no2"]),
    )


def classificar_cobertura(valor) -> str:
    """
    Converte a cobertura percentual em uma classificação explicativa.

    As faixas são critérios internos de leitura do dashboard e não uma
    classificação oficial de qualidade dos dados.
    """

    if pd.isna(valor):
        return "não pôde ser calculada"

    valor = float(valor)

    if valor >= 80:
        return "alta"

    if valor >= 50:
        return "moderada"

    return "baixa"


def exibir_interpretacao(
    dados_kpis: pd.DataFrame,
    dados_linhas: pd.DataFrame,
    dados_distancias: pd.DataFrame,
) -> None:
    """
    Gera um resumo textual determinístico dos resultados.

    Esta versão ainda não utiliza um modelo de inteligência artificial.
    As frases são construídas diretamente a partir dos dados consultados.
    """

    if dados_kpis.empty:
        return

    kpis = dados_kpis.iloc[0]

    cobertura = kpis["cobertura_ambiental_percentual"]
    classificacao = classificar_cobertura(cobertura)

    linha_destaque = "Indisponível"
    media_linha = "Indisponível"

    if not dados_linhas.empty:
        # Para fornecer um exemplo descritivo, escolhemos a linha com
        # maior média de NO2 entre aquelas que possuem valor disponível.
        linhas_validas = dados_linhas.dropna(
            subset=["media_no2"]
        )

        if not linhas_validas.empty:
            indice = linhas_validas["media_no2"].idxmax()
            linha_destaque = html.escape(
                str(
                    linhas_validas.loc[
                        indice,
                        "codigo_linha",
                    ]
                )
            )
            media_linha = formatar_decimal(
                linhas_validas.loc[
                    indice,
                    "media_no2",
                ]
            )

    faixa_proxima = "Indisponível"
    coletas_proximas = "0"

    if not dados_distancias.empty:
        primeira_faixa = dados_distancias.iloc[0]

        faixa_proxima = html.escape(
            str(primeira_faixa["faixa_distancia"])
        )

        coletas_proximas = formatar_inteiro(
            primeira_faixa["total_coletas"]
        )

    st.markdown(
        f"""
        <div class="cartao-interpretacao">
            <h3>Leitura do recorte</h3>
            <p>
                A cobertura ambiental foi de
                <strong>{formatar_percentual(cobertura)}</strong>,
                classificada nesta aplicação como
                <strong>{classificacao}</strong>.
            </p>
            <p>
                Entre as linhas com medição de NO2 disponível, a maior
                média observada ocorreu na linha
                <strong>{linha_destaque}</strong>, com valor médio de
                <strong>{media_linha}</strong>.
            </p>
            <p>
                A primeira faixa espacial disponível foi
                <strong>{faixa_proxima}</strong>, reunindo
                <strong>{coletas_proximas} coletas</strong>.
            </p>
            <p>
                Diferenças entre linhas podem decorrer de horário,
                região, estação associada, volume de observações,
                distância espacial e disponibilidade desigual dos
                poluentes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preparar_tabela_linhas(
    dados: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepara a tabela comparativa de linhas para exibição.

    Uma cópia é criada para preservar o DataFrame original utilizado
    pelos gráficos.
    """

    tabela = dados.copy()

    tabela = tabela.rename(
        columns={
            "codigo_linha": "Linha",
            "total_coletas": "Coletas",
            "total_veiculos": "Veículos",
            "total_estacoes": "Estações",
            "distancia_media": "Distância média (m)",
            "media_mp10": "MP10 médio",
            "media_mp25": "MP2.5 médio",
            "media_no": "NO médio",
            "media_no2": "NO2 médio",
            "cobertura_ambiental_percentual": "Cobertura (%)",
        }
    )

    colunas_decimais = [
        "Distância média (m)",
        "MP10 médio",
        "MP2.5 médio",
        "NO médio",
        "NO2 médio",
        "Cobertura (%)",
    ]

    for coluna in colunas_decimais:
        if coluna in tabela.columns:
            tabela[coluna] = tabela[coluna].apply(
                formatar_decimal
            )

    return tabela


def preparar_tabela_detalhada(
    dados: pd.DataFrame,
) -> pd.DataFrame:
    """
    Renomeia e formata os registros detalhados da qualidade do ar.
    """

    tabela = dados.copy()

    if "data_hora_coleta" in tabela.columns:
        tabela["data_hora_coleta"] = pd.to_datetime(
            tabela["data_hora_coleta"],
            errors="coerce",
        ).dt.strftime("%d/%m/%Y %H:%M:%S")

    tabela = tabela.rename(
        columns={
            "data_hora_coleta": "Data e hora",
            "regiao": "Região",
            "codigo_linha": "Linha",
            "prefixo_veiculo": "Veículo",
            "estacao": "Estação",
            "janela_coleta": "Janela",
            "distancia_metros": "Distância (m)",
            "faixa_distancia": "Faixa de distância",
            "mp10": "MP10",
            "mp25": "MP2.5",
            "no": "NO",
            "no2": "NO2",
        }
    )

    colunas_decimais = [
        "Distância (m)",
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
    Controla todo o fluxo da página Qualidade do Ar.

    Etapas:
    1. Exibe cabeçalho e sidebar.
    2. Executa todas as consultas com o mesmo conjunto de filtros.
    3. Mostra indicadores, gráficos e tabelas.
    4. Apresenta limitações metodológicas.
    5. Exibe detalhes técnicos caso uma exceção ocorra.
    """

    aplicar_estilo()
    exibir_cabecalho()

    try:
        filtros = exibir_sidebar_global()

        # Todas as consultas recebem o mesmo dicionário. Isso garante
        # consistência entre indicadores, gráficos e tabelas.
        dados_kpis = buscar_kpis_qualidade_ar(
            **filtros
        )

        dados_linhas = buscar_poluentes_por_linha(
            **filtros
        )

        dados_distancias = buscar_poluentes_por_distancia(
            **filtros
        )

        dados_cobertura = buscar_cobertura_por_linha(
            **filtros
        )

        dados_detalhados = buscar_detalhes_qualidade_ar(
            **filtros
        )

        exibir_filtros_ativos(filtros)

        st.divider()
        st.subheader("Indicadores ambientais")

        exibir_kpis_ambientais(dados_kpis)

        with st.expander(
            "Ver maiores valores observados",
            expanded=False,
        ):
            exibir_maximos_observados(dados_kpis)

            st.caption(
                "Os máximos são apresentados apenas como estatística "
                "descritiva. A página não os compara automaticamente "
                "com limites regulatórios."
            )

        st.divider()
        st.subheader("Relação com as linhas selecionadas")

        st.plotly_chart(
            grafico_medias_poluentes_linha(
                dados_linhas
            ),
            width="stretch",
        )

        coluna_cobertura, coluna_interpretacao = (
            st.columns(2)
        )

        with coluna_cobertura:
            st.plotly_chart(
                grafico_cobertura_ambiental_linha(
                    dados_cobertura
                ),
                width="stretch",
            )

        with coluna_interpretacao:
            exibir_interpretacao(
                dados_kpis=dados_kpis,
                dados_linhas=dados_linhas,
                dados_distancias=dados_distancias,
            )

        st.divider()
        st.subheader("Cobertura dos dados ambientais")

        coluna_geral, coluna_detalhada = st.columns(2)

        with coluna_geral:
            st.plotly_chart(
                grafico_cobertura_poluentes(
                    dados_kpis
                ),
                width="stretch",
            )

        with coluna_detalhada:
            st.plotly_chart(
                grafico_cobertura_detalhada_linha(
                    dados_cobertura
                ),
                width="stretch",
            )

        st.divider()
        st.subheader("Influência da proximidade espacial")

        st.plotly_chart(
            grafico_poluentes_por_distancia(
                dados_distancias
            ),
            width="stretch",
        )

        st.info(
            "A faixa de distância informa a proximidade entre a posição "
            "do ônibus e a estação usada na associação ambiental. "
            "Quanto maior a distância, maior deve ser a cautela ao "
            "interpretar a medição como representativa daquela posição."
        )

        st.divider()
        st.subheader("Comparação por linha")

        st.dataframe(
            preparar_tabela_linhas(dados_linhas),
            width="stretch",
            hide_index=True,
        )

        st.divider()
        st.subheader("Registros ambientais detalhados")

        st.caption(
            "A tabela exibe até 1.000 registros, ordenados da coleta "
            "mais recente para a mais antiga."
        )

        st.dataframe(
            preparar_tabela_detalhada(
                dados_detalhados
            ),
            width="stretch",
            hide_index=True,
        )

        st.divider()
        st.subheader("Limitações metodológicas")

        st.warning(
            "As medições pertencem às estações de qualidade do ar e "
            "foram associadas às posições dos ônibus por proximidade "
            "espacial e compatibilidade temporal. A análise identifica "
            "associações no conjunto de dados, mas não permite concluir "
            "que uma linha, um veículo ou o transporte público tenha "
            "causado os níveis observados de poluição."
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar a página Qualidade do Ar."
        )

        # O erro completo fica recolhido para não sobrecarregar a
        # interface, mas permanece disponível para diagnóstico.
        with st.expander("Detalhes técnicos"):
            st.exception(erro)


if __name__ == "__main__":
    main()
