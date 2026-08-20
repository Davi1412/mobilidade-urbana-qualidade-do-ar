from datetime import date

import pandas as pd
import streamlit as st

from services.consultas import buscar_opcoes_filtros


def converter_para_lista(valor) -> list[str]:
    """
    Converte os arrays retornados pelo PostgreSQL
    em listas comuns do Python.
    """

    if valor is None:
        return []

    if isinstance(valor, list):
        return valor

    if isinstance(valor, tuple):
        return list(valor)

    return list(valor)


def inicializar_estado_dos_filtros(
    regioes: list[str],
    data_inicial: date,
    data_final: date,
) -> None:
    """
    Cria os valores iniciais dos filtros somente quando
    eles ainda não existem no Session State.
    """

    valores_iniciais = {
        "filtro_regioes": regioes,
        "filtro_linhas": [],
        "filtro_veiculos": [],
        "filtro_janelas": [],
        "filtro_data_inicial": data_inicial,
        "filtro_data_final": data_final,
    }

    for chave, valor in valores_iniciais.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def solicitar_limpeza_filtros() -> None:
    """
    Registra a solicitação de limpeza.

    A alteração dos filtros será realizada no início
    da próxima execução, antes da criação dos widgets.
    """

    st.session_state["_limpar_filtros"] = True


def aplicar_limpeza_pendente(
    regioes: list[str],
    data_inicial: date,
    data_final: date,
) -> None:
    """
    Restaura os valores padrão antes da criação dos widgets.

    Isso evita o erro do Streamlit que ocorre quando uma chave
    de widget é alterada depois que o widget já foi criado.
    """

    limpeza_solicitada = st.session_state.pop(
        "_limpar_filtros",
        False,
    )

    if not limpeza_solicitada:
        return

    st.session_state["filtro_regioes"] = regioes
    st.session_state["filtro_linhas"] = []
    st.session_state["filtro_veiculos"] = []
    st.session_state["filtro_janelas"] = []
    st.session_state["filtro_data_inicial"] = data_inicial
    st.session_state["filtro_data_final"] = data_final


def validar_valores_existentes(
    regioes: list[str],
    linhas: list[str],
    veiculos: list[str],
    janelas: list[str],
) -> None:
    """
    Remove do Session State valores que não existem mais
    nas opções atuais retornadas pelo banco.
    """

    st.session_state["filtro_regioes"] = [
        valor
        for valor in st.session_state["filtro_regioes"]
        if valor in regioes
    ]

    st.session_state["filtro_linhas"] = [
        valor
        for valor in st.session_state["filtro_linhas"]
        if valor in linhas
    ]

    st.session_state["filtro_veiculos"] = [
        valor
        for valor in st.session_state["filtro_veiculos"]
        if valor in veiculos
    ]

    st.session_state["filtro_janelas"] = [
        valor
        for valor in st.session_state["filtro_janelas"]
        if valor in janelas
    ]


def exibir_sidebar_global() -> dict:
    """
    Exibe a barra lateral com os filtros globais.

    Retorna um dicionário que pode ser enviado diretamente
    às funções de consulta usando **filtros.
    """

    opcoes_df = buscar_opcoes_filtros()

    if opcoes_df.empty:
        st.sidebar.warning(
            "Não há dados disponíveis para criar os filtros."
        )

        return {
            "regioes": None,
            "linhas": None,
            "veiculos": None,
            "janelas": None,
            "data_inicial": None,
            "data_final": None,
        }

    opcoes = opcoes_df.iloc[0]

    regioes = converter_para_lista(opcoes["regioes"])
    linhas = converter_para_lista(opcoes["linhas"])
    veiculos = converter_para_lista(opcoes["veiculos"])
    janelas = converter_para_lista(opcoes["janelas"])

    data_minima = pd.to_datetime(
        opcoes["data_inicial"]
    ).date()

    data_maxima = pd.to_datetime(
        opcoes["data_final"]
    ).date()

    inicializar_estado_dos_filtros(
        regioes=regioes,
        data_inicial=data_minima,
        data_final=data_maxima,
    )

    aplicar_limpeza_pendente(
        regioes=regioes,
        data_inicial=data_minima,
        data_final=data_maxima,
    )

    validar_valores_existentes(
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
    )

    with st.sidebar:
        st.header("Filtros globais")

        st.multiselect(
            label="Regiões",
            options=regioes,
            key="filtro_regioes",
            placeholder="Todas as regiões",
        )

        st.multiselect(
            label="Linhas",
            options=linhas,
            key="filtro_linhas",
            placeholder="Todas as linhas",
        )

        st.multiselect(
            label="Veículos",
            options=veiculos,
            key="filtro_veiculos",
            placeholder="Todos os veículos",
        )

        st.multiselect(
            label="Janelas de coleta",
            options=janelas,
            key="filtro_janelas",
            placeholder="Todas as janelas",
        )

        st.date_input(
            label="Data inicial",
            min_value=data_minima,
            max_value=data_maxima,
            key="filtro_data_inicial",
            format="DD/MM/YYYY",
        )

        st.date_input(
            label="Data final",
            min_value=data_minima,
            max_value=data_maxima,
            key="filtro_data_final",
            format="DD/MM/YYYY",
        )

        data_inicial_selecionada = (
            st.session_state["filtro_data_inicial"]
        )

        data_final_selecionada = (
            st.session_state["filtro_data_final"]
        )

        periodo_invalido = (
            data_inicial_selecionada
            > data_final_selecionada
        )

        if periodo_invalido:
            st.error(
                "A data inicial não pode ser posterior "
                "à data final."
            )

        st.button(
            label="Limpar filtros",
            width="stretch",
            on_click=solicitar_limpeza_filtros,
        )

    if periodo_invalido:
        return {
            "regioes": [],
            "linhas": [],
            "veiculos": [],
            "janelas": [],
            "data_inicial": data_inicial_selecionada,
            "data_final": data_final_selecionada,
        }

    return {
        "regioes": (
            st.session_state["filtro_regioes"]
            or None
        ),
        "linhas": (
            st.session_state["filtro_linhas"]
            or None
        ),
        "veiculos": (
            st.session_state["filtro_veiculos"]
            or None
        ),
        "janelas": (
            st.session_state["filtro_janelas"]
            or None
        ),
        "data_inicial": data_inicial_selecionada,
        "data_final": data_final_selecionada,
    }