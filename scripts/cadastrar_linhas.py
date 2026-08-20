"""
cadastrar_linhas.py

Cadastra no PostgreSQL somente as linhas definidas para o projeto
Weather Report.

As linhas são consultadas na API Olho Vivo da SPTrans e vinculadas
às regiões Zona Leste e Centro.

Uso:
    python cadastrar_linhas.py
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

from db import conectar


# Carrega o token e as configurações presentes no arquivo .env.
load_dotenv()

TOKEN = os.getenv("OLHOVIVO_TOKEN")

# Endereço-base da API Olho Vivo.
BASE_URL = "http://api.olhovivo.sptrans.com.br/v2.1"

# Linhas que fazem parte oficialmente do escopo do projeto.
#
# A chave representa o nome da região no banco.
# A lista representa os códigos completos pesquisados na SPTrans.
LINHAS_POR_REGIAO = {
    "Zona Leste": [
        "4018-10",
        "3064-10",
        "407L-10",
        "407P-10",
    ],
    "Centro": [
        "917M-10",
        "875A-10",
        "669A-10",
        "715M-10",
    ],
}


def validar_configuracao() -> None:
    """
    Confirma se o token da API foi carregado corretamente.

    Evita que o programa tente autenticar usando um token vazio.
    """
    if not TOKEN:
        raise RuntimeError(
            "A variável OLHOVIVO_TOKEN não foi encontrada no arquivo .env."
        )


def autenticar() -> requests.Session:
    """
    Cria e autentica uma sessão na API Olho Vivo.

    A API utiliza cookie de sessão. Por isso, todas as chamadas seguintes
    precisam utilizar o mesmo objeto requests.Session.

    Retorna:
        requests.Session: sessão autenticada.

    Lança:
        ConnectionError: se a autenticação falhar.
    """
    validar_configuracao()

    session = requests.Session()

    url = f"{BASE_URL}/Login/Autenticar"
    resposta = session.post(
        url,
        params={"token": TOKEN},
        timeout=30,
    )

    resposta.raise_for_status()

    if resposta.text.strip().lower() != "true":
        raise ConnectionError(
            "A API Olho Vivo recusou a autenticação. Verifique o token."
        )

    print("Autenticação realizada com sucesso.")
    return session


def buscar_id_regiao(cursor, nome_regiao: str) -> int:
    """
    Busca o ID de uma região pelo nome.

    Parâmetros:
        cursor: cursor ativo do PostgreSQL.
        nome_regiao: nome exato cadastrado na tabela regiao.

    Retorna:
        int: ID da região.

    Lança:
        ValueError: caso a região não exista.
    """
    cursor.execute(
        """
        SELECT id
        FROM regiao
        WHERE nome = %s;
        """,
        (nome_regiao,),
    )

    resultado = cursor.fetchone()

    if resultado is None:
        raise ValueError(
            f"A região '{nome_regiao}' não foi encontrada no banco."
        )

    return resultado[0]


def normalizar_codigo(
    letreiro: str | None,
    sentido: Any,
) -> str:
    """
    Monta o código completo da linha no padrão usado no projeto.

    Exemplo:
        lt = "917M"
        sl = 1

        Resultado:
        "917M-10"

    A API normalmente retorna:
        lt: código-base da linha;
        sl: sentido da operação, geralmente 1 ou 2.
    """
    codigo_base = str(letreiro or "").strip().upper()
    numero_sentido = str(sentido or "").strip()

    if not codigo_base or not numero_sentido:
        return ""

    return f"{codigo_base}-{numero_sentido}0"


def buscar_linha_exata(
    session: requests.Session,
    termo: str,
) -> dict[str, Any] | None:
    """
    Pesquisa uma linha e seleciona somente o resultado exato.

    A API pode retornar mais de um registro para um termo. Por isso,
    não devemos cadastrar automaticamente todos os resultados.

    Parâmetros:
        session: sessão autenticada.
        termo: código completo, como "917M-10".

    Retorna:
        dict: registro exato retornado pela API.
        None: quando nenhum resultado exato é encontrado.
    """
    url = f"{BASE_URL}/Linha/Buscar"

    resposta = session.get(
        url,
        params={"termosBusca": termo},
        timeout=30,
    )

    resposta.raise_for_status()

    dados = resposta.json()

    if not isinstance(dados, list):
        raise ValueError(
            f"A API retornou um formato inesperado para a linha {termo}."
        )

    termo_normalizado = termo.strip().upper()

    print(f"\nResultados recebidos para {termo}:")

    for linha in dados:
        codigo_completo = normalizar_codigo(
            linha.get("lt"),
            linha.get("sl"),
        )

        print(
            "  "
            f"cl={linha.get('cl')} | "
            f"código={codigo_completo} | "
            f"tp={linha.get('tp')} | "
            f"ts={linha.get('ts')}"
        )

        if codigo_completo == termo_normalizado:
            return linha

    return None


def inserir_ou_atualizar_linha(
    cursor,
    linha: dict[str, Any],
    termo: str,
    id_regiao: int,
) -> int:
    """
    Insere ou atualiza uma linha no banco.

    Campos principais da API:
        cl: código interno usado no endpoint de posições;
        lt: código-base exibido ao passageiro;
        tp: terminal principal;
        ts: terminal secundário;
        sl: sentido da linha.

    Retorna:
        int: ID da linha inserida ou atualizada.
    """
    codigo_api = linha.get("cl")
    codigo_base = linha.get("lt")
    terminal_principal = linha.get("tp")
    terminal_secundario = linha.get("ts")
    sentido = linha.get("sl")

    if codigo_api is None:
        raise ValueError(
            f"A linha {termo} foi encontrada, mas não possui código API 'cl'."
        )

    if not codigo_base:
        raise ValueError(
            f"A linha {termo} foi encontrada, mas não possui o campo 'lt'."
        )

    # Mantemos o código completo informado no escopo, por exemplo 917M-10.
    codigo_linha = termo.upper()

    # O letreiro representa o destino principal mostrado pela API.
    letreiro = terminal_principal

    cursor.execute(
        """
        INSERT INTO linha_onibus (
            codigo_linha,
            codigo_api,
            letreiro,
            terminal_origem,
            terminal_destino,
            id_regiao
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT ON CONSTRAINT linha_unica
        DO UPDATE SET
            codigo_linha = EXCLUDED.codigo_linha,
            codigo_api = EXCLUDED.codigo_api,
            letreiro = EXCLUDED.letreiro,
            terminal_origem = EXCLUDED.terminal_origem,
            terminal_destino = EXCLUDED.terminal_destino,
            id_regiao = EXCLUDED.id_regiao
        RETURNING id;
        """,
        (
            codigo_linha,
            str(codigo_api),
            letreiro,
            terminal_principal,
            terminal_secundario,
            id_regiao,
        ),
    )

    resultado = cursor.fetchone()

    if resultado is None:
        raise RuntimeError(
            f"Não foi possível obter o ID da linha {termo} após o cadastro."
        )

    print(
        f"Cadastrada: {codigo_linha} | "
        f"API={codigo_api} | "
        f"{terminal_principal} ↔ {terminal_secundario} | "
        f"sentido={sentido}"
    )

    return resultado[0]


def cadastrar_linhas() -> None:
    """
    Coordena a autenticação, consulta da API e cadastro das oito linhas.
    """
    session = None
    conexao = None
    cursor = None

    total_cadastradas = 0
    falhas: list[str] = []

    try:
        session = autenticar()
        conexao = conectar()
        cursor = conexao.cursor()

        for nome_regiao, termos in LINHAS_POR_REGIAO.items():
            id_regiao = buscar_id_regiao(cursor, nome_regiao)

            print(f"\n=== Região: {nome_regiao} ===")

            for termo in termos:
                try:
                    linha = buscar_linha_exata(session, termo)

                    if linha is None:
                        print(
                            f"ERRO: nenhum resultado exato encontrado para {termo}."
                        )
                        falhas.append(termo)
                        continue

                    inserir_ou_atualizar_linha(
                        cursor=cursor,
                        linha=linha,
                        termo=termo,
                        id_regiao=id_regiao,
                    )

                    total_cadastradas += 1

                except (
                    requests.RequestException,
                    ValueError,
                    RuntimeError,
                ) as erro:
                    print(f"ERRO ao cadastrar {termo}: {erro}")
                    falhas.append(termo)

        if falhas:
            # Não confirma um cadastro parcialmente incorreto.
            conexao.rollback()

            raise RuntimeError(
                "O cadastro foi cancelado porque estas linhas falharam: "
                + ", ".join(falhas)
            )

        conexao.commit()

        print("\nCadastro concluído com sucesso.")
        print(f"Total cadastrado: {total_cadastradas}")

    except Exception:
        if conexao is not None:
            conexao.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None:
            conexao.close()

        if session is not None:
            session.close()


if __name__ == "__main__":
    cadastrar_linhas()