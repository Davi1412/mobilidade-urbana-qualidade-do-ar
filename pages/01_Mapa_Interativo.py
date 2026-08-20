from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from services.consultas import (
    buscar_dados_mapa,
    buscar_estacoes_mapa,
    buscar_opcoes_mapa,
)
from services.mapas import criar_mapa


st.set_page_config(
    page_title="Mapa Interativo | Weather Report",
    page_icon="🗺️",
    layout="wide",
)


def converter_array(valor) -> list[str]:
    if valor is None:
        return []

    if isinstance(valor, (list, tuple)):
        return list(valor)

    return list(valor)


st.title("🗺️ Mapa Interativo")
st.caption(
    "Visualização espacial das posições dos ônibus e das estações "
    "de monitoramento da CETESB."
)

try:
    opcoes_df = buscar_opcoes_mapa()

    if opcoes_df.empty:
        st.warning("Não há dados disponíveis para montar os filtros.")
        st.stop()

    opcoes = opcoes_df.iloc[0]
    regioes = converter_array(opcoes["regioes"])
    linhas = converter_array(opcoes["linhas"])

    data_minima = pd.to_datetime(opcoes["data_inicial"]).date()
    data_maxima = pd.to_datetime(opcoes["data_final"]).date()

    with st.sidebar:
        st.header("Filtros do mapa")

        regioes_selecionadas = st.multiselect(
            "Regiões",
            options=regioes,
            default=regioes,
        )

        linhas_selecionadas = st.multiselect(
            "Linhas",
            options=linhas,
            default=[],
            placeholder="Todas as linhas",
        )

        periodo = st.date_input(
            "Período das coletas",
            value=(data_minima, data_maxima),
            min_value=data_minima,
            max_value=data_maxima,
        )

        mostrar_ligacoes = st.checkbox(
            "Mostrar ligações ônibus–estação",
            value=True,
        )

        agrupar_onibus = st.checkbox(
            "Agrupar marcadores próximos",
            value=False,
        )

    if isinstance(periodo, tuple) and len(periodo) == 2:
        data_inicial, data_final = periodo
    else:
        data_inicial = periodo
        data_final = periodo

    dados_onibus = buscar_dados_mapa(
        regioes=regioes_selecionadas or None,
        linhas=linhas_selecionadas or None,
        data_inicial=data_inicial,
        data_final=data_final,
    )
    dados_estacoes = buscar_estacoes_mapa()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Posições exibidas", len(dados_onibus))
    col2.metric(
        "Veículos",
        dados_onibus["prefixo_veiculo"].nunique()
        if not dados_onibus.empty else 0,
    )
    col3.metric(
        "Linhas",
        dados_onibus["codigo_linha"].nunique()
        if not dados_onibus.empty else 0,
    )
    col4.metric("Estações", len(dados_estacoes))

    if dados_onibus.empty:
        st.warning("Nenhuma coleta corresponde aos filtros selecionados.")
    else:
        mapa = criar_mapa(
            dados_onibus=dados_onibus,
            dados_estacoes=dados_estacoes,
            mostrar_ligacoes=mostrar_ligacoes,
            agrupar_onibus=agrupar_onibus,
        )

        st_folium(
            mapa,
            width="stretch",
            height=680,
            returned_objects=[],
        )

        with st.expander("Dados exibidos no mapa"):
            tabela = dados_onibus[
                [
                    "prefixo_veiculo",
                    "codigo_linha",
                    "regiao",
                    "estacao",
                    "distancia_metros",
                    "data_hora_coleta",
                ]
            ].copy()

            tabela.columns = [
                "Veículo",
                "Linha",
                "Região",
                "Estação",
                "Distância (m)",
                "Data e hora",
            ]

            st.dataframe(
                tabela,
                width="stretch",
                hide_index=True,
            )

except Exception as erro:
    st.error("Não foi possível carregar o mapa interativo.")

    with st.expander("Detalhes técnicos"):
        st.exception(erro)
