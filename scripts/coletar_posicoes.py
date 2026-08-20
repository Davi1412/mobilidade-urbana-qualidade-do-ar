"""
coletar_posicoes.py

Script de coleta de dados de mobilidade para o projeto Weather Report.

Objetivo:
    Consultar a API Olho Vivo (SPTrans) e registrar a posição
    geográfica atual dos ônibus das linhas cadastradas no banco,
    associando cada coleta a uma janela de horário.

Uso no terminal:
    python coletar_posicoes.py pico_manha
    python coletar_posicoes.py meio_dia
    python coletar_posicoes.py pico_tarde
"""

import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

from db import conectar


# Carrega as variáveis configuradas no arquivo .env.
load_dotenv()

# Token de acesso à API Olho Vivo.
TOKEN = os.getenv("OLHOVIVO_TOKEN")

# Endereço-base da API.
BASE_URL = "http://api.olhovivo.sptrans.com.br/v2.1"

# Janelas de horário aceitas pelo programa.
JANELAS_VALIDAS = [
    "pico_manha",
    "meio_dia",
    "pico_tarde",
]


def autenticar():
    """
    Autentica uma sessão na API Olho Vivo.

    A API utiliza cookies de sessão. Por isso, todas as consultas
    posteriores devem usar o mesmo objeto requests.Session.

    Retorna:
        requests.Session: sessão autenticada.

    Lança:
        RuntimeError: se o token não estiver configurado.
        ConnectionError: se a autenticação for recusada.
        requests.RequestException: se houver falha HTTP ou de conexão.
    """

    # Impede que o programa tente autenticar sem token.
    if not TOKEN:
        raise RuntimeError(
            "A variável OLHOVIVO_TOKEN não foi encontrada no arquivo .env."
        )

    session = requests.Session()

    url_auth = f"{BASE_URL}/Login/Autenticar"

    resposta = session.post(
        url_auth,
        params={"token": TOKEN},
        timeout=30,
    )

    # Gera erro caso a API retorne código HTTP 4xx ou 5xx.
    resposta.raise_for_status()

    # A API retorna literalmente true quando a autenticação funciona.
    if resposta.text.strip().lower() != "true":
        session.close()

        raise ConnectionError(
            "Falha na autenticação com a API Olho Vivo. "
            "Verifique o token configurado no arquivo .env."
        )

    print("Autenticação realizada com sucesso.")

    return session


def buscar_linhas_cadastradas(cursor):
    """
    Busca as linhas válidas cadastradas no PostgreSQL.

    Apenas linhas que possuem codigo_api são retornadas. O codigo_api
    corresponde ao campo interno usado pela API para consultar posições.

    Parâmetros:
        cursor: cursor ativo da conexão PostgreSQL.

    Retorna:
        list[tuple]: lista no formato:
            (id_linha, codigo_api, codigo_linha)
    """

    cursor.execute(
        """
        SELECT
            id,
            codigo_api,
            codigo_linha
        FROM linha_onibus
        WHERE codigo_api IS NOT NULL
          AND TRIM(codigo_api) <> ''
        ORDER BY codigo_linha;
        """
    )

    return cursor.fetchall()


def buscar_veiculos(session, codigo_api, codigo_linha):
    """
    Consulta a posição dos veículos de uma linha.

    Parâmetros:
        session: sessão autenticada da API.
        codigo_api: identificador interno da linha na SPTrans.
        codigo_linha: código legível, como 917M-10.

    Retorna:
        list[dict]: lista de veículos retornada pela API.

    Caso ocorra algum erro, retorna uma lista vazia.
    """

    url_posicao = f"{BASE_URL}/Posicao/Linha"

    try:
        resposta = session.get(
            url_posicao,
            params={"codigoLinha": codigo_api},
            timeout=30,
        )

        # Verifica códigos HTTP de erro.
        resposta.raise_for_status()

        # Converte a resposta em JSON.
        dados = resposta.json()

    except requests.Timeout:
        print(
            f"Linha {codigo_linha} "
            f"(código API {codigo_api}): tempo limite excedido."
        )
        return []

    except requests.RequestException as erro:
        print(
            f"Linha {codigo_linha} "
            f"(código API {codigo_api}): erro na requisição: {erro}"
        )
        return []

    except ValueError:
        print(
            f"Linha {codigo_linha} "
            f"(código API {codigo_api}): a API retornou um JSON inválido."
        )
        return []

    # Confirma se o JSON possui o formato esperado.
    if not isinstance(dados, dict):
        print(
            f"Linha {codigo_linha} "
            f"(código API {codigo_api}): formato de resposta inesperado."
        )
        return []

    # A lista de veículos fica na chave "vs".
    veiculos = dados.get("vs", [])

    if not isinstance(veiculos, list):
        print(
            f"Linha {codigo_linha} "
            f"(código API {codigo_api}): campo 'vs' inválido."
        )
        return []

    return veiculos


def salvar_veiculo(
    cursor,
    id_linha,
    veiculo,
    janela_coleta,
    data_hora_coleta,
):
    """
    Salva uma posição de veículo no PostgreSQL.

    A geometria é criada automaticamente pelo gatilho do banco.
    """

    prefixo = veiculo.get("p")
    latitude = veiculo.get("py")
    longitude = veiculo.get("px")

    if latitude is None or longitude is None:
        print(
            f"Veículo {prefixo or 'sem prefixo'} ignorado: "
            "latitude ou longitude ausente."
        )
        return False

    cursor.execute(
        """
        INSERT INTO coleta_posicao_veiculo (
            id_linha,
            prefixo_veiculo,
            latitude,
            longitude,
            janela_coleta,
            data_hora_coleta
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            id_linha,
            prefixo,
            latitude,
            longitude,
            janela_coleta,
            data_hora_coleta,
        ),
    )

    return True


def coletar_posicoes(janela_coleta):
    """
    Executa o processo completo de coleta.

    Fluxo:
        1. Valida a janela informada.
        2. Autentica na API Olho Vivo.
        3. Conecta ao PostgreSQL.
        4. Busca as linhas cadastradas.
        5. Consulta os veículos de cada linha.
        6. Salva as posições encontradas.
        7. Confirma a transação.
    """

    # Valida a janela recebida pelo terminal.
    if janela_coleta not in JANELAS_VALIDAS:
        raise ValueError(
            f"Janela inválida: '{janela_coleta}'. "
            f"Use uma destas opções: {JANELAS_VALIDAS}"
        )

    session = None
    conexao = None
    cursor = None

    total_veiculos = 0
    total_linhas_com_veiculos = 0
    total_linhas_sem_veiculos = 0

    try:
        # Autentica na API.
        session = autenticar()

        # Abre a conexão com o banco.
        conexao = conectar()
        cursor = conexao.cursor()

        # Busca apenas linhas com código válido da API.
        linhas = buscar_linhas_cadastradas(cursor)

        print(
            f"\nColetando posições para "
            f"{len(linhas)} linha(s) cadastrada(s)...\n"
        )

        if not linhas:
            print(
                "Nenhuma linha com codigo_api válido foi encontrada no banco."
            )
            return

        # Percorre cada linha cadastrada.
        for id_linha, codigo_api, codigo_linha in linhas:
            print(
                f"Consultando linha {codigo_linha} "
                f"(código API {codigo_api})..."
            )

            veiculos = buscar_veiculos(
                session=session,
                codigo_api=codigo_api,
                codigo_linha=codigo_linha,
            )

            if not veiculos:
                print(
                    f"Linha {codigo_linha}: "
                    "nenhum veículo retornado neste momento.\n"
                )

                total_linhas_sem_veiculos += 1
                continue

            # Usa o mesmo horário para todos os veículos desta linha.
            data_hora_coleta = datetime.now()

            veiculos_salvos = 0

            for veiculo in veiculos:
                salvo = salvar_veiculo(
                    cursor=cursor,
                    id_linha=id_linha,
                    veiculo=veiculo,
                    janela_coleta=janela_coleta,
                    data_hora_coleta=data_hora_coleta,
                )

                if salvo:
                    veiculos_salvos += 1
                    total_veiculos += 1

            if veiculos_salvos > 0:
                total_linhas_com_veiculos += 1

            print(
                f"Linha {codigo_linha}: "
                f"{veiculos_salvos} veículo(s) registrado(s).\n"
            )

        # Confirma todas as inserções.
        conexao.commit()

        print("=" * 60)
        print("Coleta concluída com sucesso.")
        print(f"Janela: {janela_coleta}")
        print(f"Linhas consultadas: {len(linhas)}")
        print(f"Linhas com veículos: {total_linhas_com_veiculos}")
        print(f"Linhas sem veículos: {total_linhas_sem_veiculos}")
        print(f"Total de veículos registrados: {total_veiculos}")
        print("=" * 60)

    except Exception:
        # Desfaz inserções parciais caso ocorra algum erro inesperado.
        if conexao is not None:
            conexao.rollback()

        raise

    finally:
        # Fecha os recursos mesmo em caso de erro.
        if cursor is not None:
            cursor.close()

        if conexao is not None:
            conexao.close()

        if session is not None:
            session.close()


if __name__ == "__main__":
    # O programa exige exatamente um argumento:
    # pico_manha, meio_dia ou pico_tarde.
    if len(sys.argv) != 2:
        print("Uso:")
        print("    python coletar_posicoes.py <janela>")
        print()
        print("Janelas válidas:")
        print("    pico_manha")
        print("    meio_dia")
        print("    pico_tarde")
        sys.exit(1)

    janela = sys.argv[1].strip().lower()

    try:
        coletar_posicoes(janela)

    except Exception as erro:
        print(f"\nErro durante a coleta: {erro}")
        sys.exit(1)