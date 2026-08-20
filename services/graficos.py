from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def criar_grafico_vazio(
    titulo: str,
    mensagem: str = "Não há dados para os filtros selecionados.",
) -> go.Figure:
    """
    Cria uma figura vazia com uma mensagem centralizada.
    """

    figura = go.Figure()

    figura.add_annotation(
        text=mensagem,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=15),
    )

    figura.update_layout(
        title=titulo,
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return figura


def aplicar_layout_padrao(
    figura: go.Figure,
    altura: int = 420,
) -> go.Figure:
    """
    Aplica configurações visuais compartilhadas pelos gráficos.
    """

    figura.update_layout(
        height=altura,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text=None,
    )

    return figura


def preparar_dados_poluentes(
    dados: pd.DataFrame,
    coluna_identificadora: str,
    colunas_poluentes: dict[str, str],
) -> pd.DataFrame:
    """
    Converte colunas de poluentes para o formato longo usado pelo Plotly.
    """

    colunas_disponiveis = [
        coluna
        for coluna in colunas_poluentes
        if coluna in dados.columns
    ]

    if not colunas_disponiveis:
        return pd.DataFrame()

    dados_formatados = dados.melt(
        id_vars=[coluna_identificadora],
        value_vars=colunas_disponiveis,
        var_name="coluna_poluente",
        value_name="valor",
    )

    dados_formatados = dados_formatados.dropna(
        subset=["valor"]
    )

    dados_formatados["poluente"] = (
        dados_formatados["coluna_poluente"].map(
            colunas_poluentes
        )
    )

    return dados_formatados


# ----------------------------------------------------------------------
# GRÁFICOS DA HOME
# ----------------------------------------------------------------------


def grafico_coletas_regiao(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Exibe a quantidade de coletas agrupada por região.
    """

    titulo = "Coletas por região"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    figura = px.bar(
        dados,
        x="regiao",
        y="total_coletas",
        color="regiao",
        text="total_coletas",
        labels={
            "regiao": "Região",
            "total_coletas": "Quantidade de coletas",
        },
        title=titulo,
    )

    figura.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Coletas: %{y}<extra></extra>"
        ),
    )

    figura.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Coletas",
    )

    return aplicar_layout_padrao(figura)


def grafico_poluentes(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Compara as médias de MP10, MP2.5, NO e NO2 por região.
    """

    titulo = "Média dos poluentes por região"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    colunas_poluentes = {
        "mp10": "MP10",
        "mp25": "MP2.5",
        "no": "NO",
        "no2": "NO2",
    }

    dados_formatados = preparar_dados_poluentes(
        dados=dados,
        coluna_identificadora="regiao",
        colunas_poluentes=colunas_poluentes,
    )

    if dados_formatados.empty:
        return criar_grafico_vazio(
            titulo,
            "Não há medições ambientais no período selecionado.",
        )

    figura = px.bar(
        dados_formatados,
        x="poluente",
        y="valor",
        color="regiao",
        barmode="group",
        labels={
            "poluente": "Poluente",
            "valor": "Concentração média",
            "regiao": "Região",
        },
        title=titulo,
    )

    figura.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Média: %{y:.2f}<extra></extra>"
        ),
    )

    figura.update_layout(
        xaxis_title=None,
        yaxis_title="Concentração média",
        legend_title_text="Região",
    )

    return aplicar_layout_padrao(figura)


def grafico_fluxo_linhas(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Exibe as linhas com maior quantidade de coletas.
    """

    titulo = "Linhas mais observadas"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    dados_ordenados = dados.sort_values(
        by=["total_coletas", "codigo_linha"],
        ascending=[True, False],
    )

    figura = px.bar(
        dados_ordenados,
        x="total_coletas",
        y="codigo_linha",
        orientation="h",
        text="total_coletas",
        labels={
            "codigo_linha": "Linha",
            "total_coletas": "Quantidade de coletas",
        },
        title=titulo,
        custom_data=[
            "total_veiculos",
            "distancia_media",
        ],
    )

    figura.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>Linha %{y}</b><br>"
            "Coletas: %{x}<br>"
            "Veículos distintos: %{customdata[0]}<br>"
            "Distância média: %{customdata[1]:.2f} m"
            "<extra></extra>"
        ),
    )

    figura.update_layout(
        showlegend=False,
        xaxis_title="Coletas",
        yaxis_title=None,
    )

    return aplicar_layout_padrao(figura)


def grafico_distribuicao_distancias(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Exibe a quantidade e o percentual de coletas por faixa de distância.
    """

    titulo = "Distribuição das distâncias"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    figura = px.bar(
        dados,
        x="faixa_distancia",
        y="total_coletas",
        text="percentual",
        labels={
            "faixa_distancia": "Faixa de distância",
            "total_coletas": "Quantidade de coletas",
            "percentual": "Percentual",
        },
        title=titulo,
        custom_data=["percentual"],
    )

    figura.update_traces(
        texttemplate="%{customdata[0]:.1f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Coletas: %{y}<br>"
            "Participação: %{customdata[0]:.2f}%"
            "<extra></extra>"
        ),
    )

    figura.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Coletas",
    )

    return aplicar_layout_padrao(figura)


# ----------------------------------------------------------------------
# GRÁFICOS DA PÁGINA QUALIDADE DO AR
# ----------------------------------------------------------------------


def grafico_medias_poluentes_linha(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Compara as médias dos poluentes entre as linhas de ônibus.
    """

    titulo = "Médias dos poluentes por linha"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    colunas_poluentes = {
        "media_mp10": "MP10",
        "media_mp25": "MP2.5",
        "media_no": "NO",
        "media_no2": "NO2",
    }

    dados_formatados = preparar_dados_poluentes(
        dados=dados,
        coluna_identificadora="codigo_linha",
        colunas_poluentes=colunas_poluentes,
    )

    if dados_formatados.empty:
        return criar_grafico_vazio(
            titulo,
            "Não há medições ambientais disponíveis por linha.",
        )

    figura = px.bar(
        dados_formatados,
        x="codigo_linha",
        y="valor",
        color="poluente",
        barmode="group",
        labels={
            "codigo_linha": "Linha",
            "valor": "Concentração média",
            "poluente": "Poluente",
        },
        title=titulo,
    )

    figura.update_traces(
        hovertemplate=(
            "<b>Linha %{x}</b><br>"
            "Média: %{y:.2f}<extra></extra>"
        ),
    )

    figura.update_layout(
        xaxis_title="Linha",
        yaxis_title="Concentração média",
        legend_title_text="Poluente",
    )

    return aplicar_layout_padrao(figura, altura=460)


def grafico_poluentes_por_distancia(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Compara as médias ambientais entre as faixas de distância.
    """

    titulo = "Poluentes por faixa de distância"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    colunas_poluentes = {
        "media_mp10": "MP10",
        "media_mp25": "MP2.5",
        "media_no": "NO",
        "media_no2": "NO2",
    }

    dados_formatados = preparar_dados_poluentes(
        dados=dados,
        coluna_identificadora="faixa_distancia",
        colunas_poluentes=colunas_poluentes,
    )

    if dados_formatados.empty:
        return criar_grafico_vazio(
            titulo,
            "Não há medições ambientais disponíveis por distância.",
        )

    figura = px.line(
        dados_formatados,
        x="faixa_distancia",
        y="valor",
        color="poluente",
        markers=True,
        labels={
            "faixa_distancia": "Faixa de distância",
            "valor": "Concentração média",
            "poluente": "Poluente",
        },
        title=titulo,
    )

    figura.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Média: %{y:.2f}<extra></extra>"
        ),
    )

    figura.update_layout(
        xaxis_title=None,
        yaxis_title="Concentração média",
        legend_title_text="Poluente",
    )

    return aplicar_layout_padrao(figura, altura=460)


def grafico_cobertura_ambiental_linha(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Exibe a cobertura ambiental geral por linha de ônibus.
    """

    titulo = "Cobertura ambiental por linha"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    dados_ordenados = dados.sort_values(
        by=[
            "cobertura_ambiental_percentual",
            "codigo_linha",
        ],
        ascending=[True, False],
    )

    figura = px.bar(
        dados_ordenados,
        x="cobertura_ambiental_percentual",
        y="codigo_linha",
        orientation="h",
        text="cobertura_ambiental_percentual",
        labels={
            "codigo_linha": "Linha",
            "cobertura_ambiental_percentual": (
                "Cobertura ambiental (%)"
            ),
        },
        title=titulo,
        custom_data=[
            "total_coletas",
            "total_veiculos",
        ],
    )

    figura.update_traces(
        texttemplate="%{x:.1f}%",
        textposition="outside",
        hovertemplate=(
            "<b>Linha %{y}</b><br>"
            "Cobertura geral: %{x:.2f}%<br>"
            "Coletas: %{customdata[0]}<br>"
            "Veículos distintos: %{customdata[1]}"
            "<extra></extra>"
        ),
    )

    figura.update_xaxes(
        range=[0, 105],
        ticksuffix="%",
    )

    figura.update_layout(
        showlegend=False,
        xaxis_title="Cobertura ambiental",
        yaxis_title=None,
    )

    return aplicar_layout_padrao(figura, altura=460)


def grafico_cobertura_poluentes(
    dados_kpis: pd.DataFrame,
) -> go.Figure:
    """
    Compara a disponibilidade individual de MP10, MP2.5, NO e NO2.
    """

    titulo = "Cobertura por poluente"

    if dados_kpis.empty:
        return criar_grafico_vazio(titulo)

    kpis = dados_kpis.iloc[0]

    dados = pd.DataFrame(
        {
            "poluente": [
                "MP10",
                "MP2.5",
                "NO",
                "NO2",
            ],
            "cobertura": [
                kpis.get("cobertura_mp10_percentual"),
                kpis.get("cobertura_mp25_percentual"),
                kpis.get("cobertura_no_percentual"),
                kpis.get("cobertura_no2_percentual"),
            ],
        }
    )

    dados = dados.dropna(subset=["cobertura"])

    if dados.empty:
        return criar_grafico_vazio(
            titulo,
            "Não há informações de cobertura disponíveis.",
        )

    figura = px.bar(
        dados,
        x="poluente",
        y="cobertura",
        text="cobertura",
        labels={
            "poluente": "Poluente",
            "cobertura": "Cobertura (%)",
        },
        title=titulo,
    )

    figura.update_traces(
        texttemplate="%{y:.1f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Cobertura: %{y:.2f}%"
            "<extra></extra>"
        ),
    )

    figura.update_yaxes(
        range=[0, 105],
        ticksuffix="%",
    )

    figura.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Cobertura",
    )

    return aplicar_layout_padrao(figura)


def grafico_cobertura_detalhada_linha(
    dados: pd.DataFrame,
) -> go.Figure:
    """
    Compara a cobertura de cada poluente entre as linhas de ônibus.
    """

    titulo = "Cobertura detalhada por linha e poluente"

    if dados.empty:
        return criar_grafico_vazio(titulo)

    colunas_cobertura = {
        "cobertura_mp10_percentual": "MP10",
        "cobertura_mp25_percentual": "MP2.5",
        "cobertura_no_percentual": "NO",
        "cobertura_no2_percentual": "NO2",
    }

    dados_formatados = preparar_dados_poluentes(
        dados=dados,
        coluna_identificadora="codigo_linha",
        colunas_poluentes=colunas_cobertura,
    )

    if dados_formatados.empty:
        return criar_grafico_vazio(
            titulo,
            "Não há dados de cobertura por linha.",
        )

    figura = px.bar(
        dados_formatados,
        x="codigo_linha",
        y="valor",
        color="poluente",
        barmode="group",
        labels={
            "codigo_linha": "Linha",
            "valor": "Cobertura (%)",
            "poluente": "Poluente",
        },
        title=titulo,
    )

    figura.update_traces(
        hovertemplate=(
            "<b>Linha %{x}</b><br>"
            "Cobertura: %{y:.2f}%"
            "<extra></extra>"
        ),
    )

    figura.update_yaxes(
        range=[0, 105],
        ticksuffix="%",
    )

    figura.update_layout(
        xaxis_title="Linha",
        yaxis_title="Cobertura",
        legend_title_text="Poluente",
    )

    return aplicar_layout_padrao(figura, altura=460)
