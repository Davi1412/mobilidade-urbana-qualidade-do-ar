from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from components.sidebar import exibir_sidebar_global
from services.consultas import (
    buscar_cobertura_por_linha,
    buscar_kpis_qualidade_ar,
    buscar_poluentes_por_distancia,
    buscar_poluentes_por_linha,
)
from services.ollama_service import (
    ErroOllama,
    construir_contexto_analise,
    gerar_resposta_stream,
    listar_modelos_instalados,
)


st.set_page_config(
    page_title="Assistente IA | Weather Report",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


PERGUNTAS_SUGERIDAS = [
    "Resuma os principais resultados do recorte selecionado.",
    "Qual linha apresentou as maiores médias de poluentes?",
    "A cobertura ambiental é suficiente para comparar as linhas?",
    "Como a distância até a estação afeta a interpretação?",
    "Quais limitações metodológicas devo mencionar na análise?",
]


def aplicar_estilo() -> None:
    """
    Aplica estilos específicos da página do assistente.
    """

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }

            .cabecalho-ia {
                padding: 1.3rem 1.5rem;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 1rem;
                margin-bottom: 1rem;
            }

            .cabecalho-ia h1 {
                margin: 0;
                font-size: 2.05rem;
            }

            .cabecalho-ia p {
                margin: 0.45rem 0 0;
                opacity: 0.8;
                line-height: 1.5;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def exibir_cabecalho() -> None:
    """
    Exibe o título e o escopo funcional do assistente.
    """

    st.markdown(
        """
        <div class="cabecalho-ia">
            <h1>🤖 Assistente de Análise</h1>
            <p>
                O modelo local interpreta os indicadores agregados do
                recorte atual. Ele não acessa diretamente o PostgreSQL,
                não executa SQL e não recebe os registros brutos.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=30, show_spinner=False)
def carregar_modelos() -> list[str]:
    """
    Consulta os modelos locais e mantém o resultado em cache por
    poucos segundos para evitar chamadas repetidas ao Ollama.
    """

    return listar_modelos_instalados()


def inicializar_estado() -> None:
    """
    Inicializa o histórico e a pergunta sugerida da sessão.
    """

    if "historico_assistente_ia" not in st.session_state:
        st.session_state.historico_assistente_ia = []

    if "pergunta_assistente_ia" not in st.session_state:
        st.session_state.pergunta_assistente_ia = ""


def limpar_conversa() -> None:
    """
    Remove apenas o histórico do chat da sessão atual.
    """

    st.session_state.historico_assistente_ia = []
    st.session_state.pergunta_assistente_ia = ""


def selecionar_pergunta_sugerida(
    pergunta: str,
) -> None:
    """
    Copia uma pergunta sugerida para o campo de entrada.
    """

    st.session_state.pergunta_assistente_ia = pergunta


def exibir_resumo_contexto(
    contexto: dict,
) -> None:
    """
    Mostra ao usuário quais dados serão enviados ao modelo.
    """

    indicadores = contexto.get(
        "indicadores_ambientais",
        [],
    )

    indicador = (
        indicadores[0]
        if indicadores
        else {}
    )

    colunas = st.columns(4)

    colunas[0].metric(
        "Coletas",
        int(
            indicador.get(
                "total_coletas",
                0,
            )
            or 0
        ),
    )

    colunas[1].metric(
        "Estações",
        int(
            indicador.get(
                "total_estacoes",
                0,
            )
            or 0
        ),
    )

    cobertura = indicador.get(
        "cobertura_ambiental_percentual"
    )

    cobertura_texto = (
        f"{float(cobertura):.2f}%"
        if cobertura is not None
        else "Indisponível"
    )

    colunas[2].metric(
        "Cobertura ambiental",
        cobertura_texto,
    )

    colunas[3].metric(
        "Linhas no contexto",
        len(
            contexto.get(
                "poluentes_por_linha",
                [],
            )
        ),
    )

    with st.expander(
        "Visualizar contexto estruturado enviado à IA",
        expanded=False,
    ):
        st.code(
            json.dumps(
                contexto,
                ensure_ascii=False,
                indent=2,
            ),
            language="json",
        )


def exibir_historico() -> None:
    """
    Renderiza as mensagens anteriores armazenadas na sessão.
    """

    for mensagem in st.session_state.historico_assistente_ia:
        with st.chat_message(
            mensagem["role"]
        ):
            st.markdown(
                mensagem["content"]
            )


def main() -> None:
    """
    Orquestra filtros, consultas, contexto e conversa com o Ollama.
    """

    aplicar_estilo()
    inicializar_estado()
    exibir_cabecalho()

    try:
        filtros = exibir_sidebar_global()

        # O modelo recebe somente resultados agregados das consultas
        # controladas já usadas pela página Qualidade do Ar.
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

        contexto = construir_contexto_analise(
            filtros=filtros,
            dados_kpis=dados_kpis,
            dados_linhas=dados_linhas,
            dados_distancias=dados_distancias,
            dados_cobertura=dados_cobertura,
        )

        try:
            modelos = carregar_modelos()
        except ErroOllama as erro:
            st.error(str(erro))
            st.stop()

        if not modelos:
            st.warning(
                "Nenhum modelo foi encontrado no Ollama. "
                "Baixe um modelo com `ollama pull nome-do-modelo`."
            )
            st.stop()

        coluna_modelo, coluna_limpar = st.columns(
            [4, 1]
        )

        with coluna_modelo:
            modelo = st.selectbox(
                "Modelo local",
                options=modelos,
                help=(
                    "A lista é obtida diretamente da instalação "
                    "local do Ollama."
                ),
            )

        with coluna_limpar:
            st.write("")
            st.write("")

            st.button(
                "Limpar conversa",
                on_click=limpar_conversa,
                width="stretch",
            )

        exibir_resumo_contexto(contexto)

        st.divider()
        st.subheader("Perguntas sugeridas")

        colunas_perguntas = st.columns(2)

        for indice, pergunta in enumerate(
            PERGUNTAS_SUGERIDAS
        ):
            coluna = colunas_perguntas[
                indice % 2
            ]

            coluna.button(
                pergunta,
                key=f"pergunta_sugerida_{indice}",
                on_click=selecionar_pergunta_sugerida,
                args=(pergunta,),
                width="stretch",
            )

        st.divider()
        st.subheader("Conversa")

        exibir_historico()

        pergunta = st.chat_input(
            "Faça uma pergunta sobre o recorte selecionado.",
            key="pergunta_assistente_ia",
        )

        if pergunta:
            # A pergunta é adicionada antes da chamada para que ela
            # apareça imediatamente na interface.
            with st.chat_message("user"):
                st.markdown(pergunta)

            historico_anterior = (
                st.session_state.historico_assistente_ia.copy()
            )

            st.session_state.historico_assistente_ia.append(
                {
                    "role": "user",
                    "content": pergunta,
                }
            )

            with st.chat_message("assistant"):
                try:
                    resposta = st.write_stream(
                        gerar_resposta_stream(
                            modelo=modelo,
                            pergunta=pergunta,
                            contexto=contexto,
                            historico=historico_anterior,
                        )
                    )

                except ErroOllama as erro:
                    st.error(str(erro))
                    resposta = ""

            if resposta:
                st.session_state.historico_assistente_ia.append(
                    {
                        "role": "assistant",
                        "content": resposta,
                    }
                )

        st.divider()

        st.caption(
            "A resposta é gerada por um modelo local. Revise as "
            "conclusões antes de utilizá-las em trabalhos acadêmicos "
            "ou decisões operacionais."
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar o Assistente de Análise."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(erro)


if __name__ == "__main__":
    main()
