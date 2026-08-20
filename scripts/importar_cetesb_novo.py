"""Importador automático de arquivos CSV da CETESB.

Uso recomendado:
    python importar_cetesb_novo.py dados_brutos/cetesb_atualizados

Também aceita um ou vários arquivos:
    python importar_cetesb_novo.py arquivo1.csv arquivo2.csv

Sem argumentos, procura CSVs em:
    dados_brutos/cetesb_atualizados

O módulo ``db.py`` do projeto deve disponibilizar a função ``conectar()``.
"""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator

# Permite executar tanto pela raiz (python -m scripts.importar_cetesb_novo)
# quanto diretamente (python scripts/importar_cetesb_novo.py).
try:
    from db import conectar
except ModuleNotFoundError:
    raiz_projeto = Path(__file__).resolve().parents[1]
    if str(raiz_projeto) not in sys.path:
        sys.path.insert(0, str(raiz_projeto))
    from db import conectar


PASTA_PADRAO = Path("dados_brutos/cetesb_atualizados")
UNIDADE_PADRAO = "ug/m3"


@dataclass(frozen=True)
class Medicao:
    estacao: str
    poluente: str
    valor: float
    unidade: str
    data_hora: datetime


@dataclass
class ResultadoArquivo:
    arquivo: Path
    lidas: int = 0
    inseridas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0
    erros: int = 0


def normalizar_texto(valor: object) -> str:
    """Remove acentos, espaços extras e diferenças de caixa para comparação."""
    texto = "" if valor is None else str(valor).strip()
    texto = " ".join(texto.split())
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.casefold()


def detectar_codificacao(caminho: Path) -> str:
    """Detecta as codificações mais comuns dos arquivos exportados pela CETESB."""
    amostra = caminho.read_bytes()[:8192]
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            amostra.decode(codificacao)
            return codificacao
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detectar_delimitador(caminho: Path, codificacao: str) -> str:
    with caminho.open("r", encoding=codificacao, newline="") as arquivo:
        amostra = arquivo.read(4096)
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";,\t").delimiter
    except csv.Error:
        return ";" if ";" in amostra else ","


def localizar_coluna(cabecalhos: Iterable[str], *nomes: str) -> str | None:
    mapa = {normalizar_texto(c): c for c in cabecalhos if c is not None}
    for nome in nomes:
        encontrada = mapa.get(normalizar_texto(nome))
        if encontrada:
            return encontrada
    return None


def converter_poluente(nome_parametro: str) -> str:
    nome = normalizar_texto(nome_parametro).replace(" ", "")
    if nome.startswith("mp2.5") or nome.startswith("mp25"):
        return "MP2.5"
    if nome.startswith("mp10"):
        return "MP10"
    if nome.startswith("no2"):
        return "NO2"
    if nome.startswith("no"):
        return "NO"
    raise ValueError(f"Poluente não reconhecido: {nome_parametro!r}")


def converter_valor(valor_texto: str) -> float:
    texto = str(valor_texto).strip().replace(" ", "")
    if texto in {"", "-", "--", "null", "NULL", "nan", "NaN"}:
        raise ValueError("valor ausente")

    # Formatos brasileiros: 1.234,56 ou 12,5.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def converter_data_hora(data_texto: str, hora_texto: str | None = None) -> datetime:
    if hora_texto is None:
        texto = str(data_texto).strip()
        formatos = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        )
        for formato in formatos:
            try:
                return datetime.strptime(texto, formato)
            except ValueError:
                pass
        raise ValueError(f"Data/hora inválida: {texto!r}")

    data = str(data_texto).strip()
    hora = str(hora_texto).strip()

    # Algumas exportações usam 24:00 para representar 00:00 do dia seguinte.
    if hora.startswith("24:"):
        base = datetime.strptime(data, "%d/%m/%Y") + timedelta(days=1)
        minutos_segundos = hora.split(":")[1:]
        minutos = int(minutos_segundos[0]) if minutos_segundos else 0
        segundos = int(minutos_segundos[1]) if len(minutos_segundos) > 1 else 0
        return base.replace(minute=minutos, second=segundos)

    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(f"{data} {hora}", formato)
        except ValueError:
            pass
    raise ValueError(f"Data/hora inválida: {data!r} {hora!r}")


def normalizar_unidade(unidade: str | None) -> str:
    texto = normalizar_texto(unidade or "")
    if "g/m3" in texto or "g/m³" in texto:
        return UNIDADE_PADRAO
    return str(unidade).strip() if unidade and str(unidade).strip() else UNIDADE_PADRAO


def extrair_unidade_cabecalho(cabecalho: str) -> str:
    """Extrai a unidade de cabeçalhos como ``MP10(...) - µg/m3``."""
    partes = str(cabecalho).rsplit("-", 1)
    return normalizar_unidade(partes[-1] if len(partes) == 2 else "")


def ler_relatorio_cetesb(
    linhas: list[list[str]], caminho: Path
) -> Iterator[Medicao] | None:
    """Lê o relatório matricial exportado atualmente pelo sistema QUALAR.

    O arquivo possui metadados no topo, uma linha ``Data;Hora;...``, outra
    linha com os nomes dos poluentes e, depois, uma coluna por poluente.
    """
    estacao = ""
    indice_cabecalho: int | None = None

    for indice, linha in enumerate(linhas):
        primeira = normalizar_texto(linha[0] if linha else "").rstrip(":")
        if primeira == "nome da estacao" and len(linha) > 1:
            estacao = str(linha[1]).strip()
        if (
            len(linha) >= 2
            and normalizar_texto(linha[0]) == "data"
            and normalizar_texto(linha[1]) == "hora"
        ):
            indice_cabecalho = indice
            break

    if not estacao or indice_cabecalho is None:
        return None
    if indice_cabecalho + 1 >= len(linhas):
        raise ValueError(f"Cabeçalho de poluentes incompleto em {caminho.name}.")

    linha_parametros = linhas[indice_cabecalho + 1]
    parametros: dict[int, tuple[str, str]] = {}
    for coluna, cabecalho in enumerate(linha_parametros[2:], start=2):
        if not str(cabecalho).strip():
            continue
        try:
            parametros[coluna] = (
                converter_poluente(cabecalho),
                extrair_unidade_cabecalho(cabecalho),
            )
        except ValueError as erro:
            print(f"  Aviso: coluna ignorada: {erro}")

    if not parametros:
        raise ValueError("Nenhum poluente reconhecido no relatório da CETESB.")

    def gerar() -> Iterator[Medicao]:
        for numero_linha, linha in enumerate(
            linhas[indice_cabecalho + 2 :], start=indice_cabecalho + 3
        ):
            if len(linha) < 2 or not str(linha[0]).strip():
                continue
            for coluna, (poluente, unidade) in parametros.items():
                valor_texto = linha[coluna] if coluna < len(linha) else ""
                try:
                    valor = converter_valor(valor_texto)
                    data_hora = converter_data_hora(linha[0], linha[1])
                    yield Medicao(
                        estacao=estacao,
                        poluente=poluente,
                        valor=valor,
                        unidade=unidade,
                        data_hora=data_hora,
                    )
                except ValueError as erro:
                    if str(erro) != "valor ausente":
                        print(f"  Aviso: linha {numero_linha} ignorada: {erro}")

    return gerar()


def ler_formato_tabular(
    caminho: Path, codificacao: str, delimitador: str
) -> Iterator[Medicao]:
    """Mantém compatibilidade com CSVs normalizados (uma medição por linha)."""

    with caminho.open("r", encoding=codificacao, newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=delimitador)
        cabecalhos = leitor.fieldnames or []

        # Formato original exportado pela CETESB.
        col_estacao = localizar_coluna(cabecalhos, "Nome Estação", "estacao")
        col_parametro = localizar_coluna(cabecalhos, "Nome Parâmetro", "poluente")
        col_valor = localizar_coluna(cabecalhos, "Média Horária", "valor")
        col_unidade = localizar_coluna(cabecalhos, "Unidade Medida", "unidade")
        col_data = localizar_coluna(cabecalhos, "Data")
        col_hora = localizar_coluna(cabecalhos, "Hora")
        col_data_hora = localizar_coluna(cabecalhos, "data_hora")
        col_valido = localizar_coluna(cabecalhos, "Válido", "Valido")

        obrigatorias = {
            "estação": col_estacao,
            "poluente": col_parametro,
            "valor": col_valor,
        }
        ausentes = [nome for nome, coluna in obrigatorias.items() if coluna is None]
        if col_data_hora is None and (col_data is None or col_hora is None):
            ausentes.append("data/hora")
        if ausentes:
            raise ValueError(
                "Colunas obrigatórias não encontradas: " + ", ".join(ausentes)
            )

        for numero_linha, linha in enumerate(leitor, start=2):
            try:
                if col_valido:
                    situacao = normalizar_texto(linha.get(col_valido, ""))
                    if situacao and situacao not in {"sim", "valido", "valid"}:
                        continue

                valor = converter_valor(linha.get(col_valor, ""))
                if col_data_hora:
                    data_hora = converter_data_hora(linha.get(col_data_hora, ""))
                else:
                    data_hora = converter_data_hora(
                        linha.get(col_data, ""), linha.get(col_hora, "")
                    )

                yield Medicao(
                    estacao=str(linha.get(col_estacao, "")).strip(),
                    poluente=converter_poluente(str(linha.get(col_parametro, ""))),
                    valor=valor,
                    unidade=normalizar_unidade(
                        linha.get(col_unidade, "") if col_unidade else ""
                    ),
                    data_hora=data_hora,
                )
            except ValueError as erro:
                # Valor ausente é comum nos arquivos ambientais e não interrompe a importação.
                if str(erro) != "valor ausente":
                    print(f"  Aviso: linha {numero_linha} ignorada: {erro}")
                continue


def ler_medicoes(caminho: Path) -> Iterator[Medicao]:
    codificacao = detectar_codificacao(caminho)
    delimitador = detectar_delimitador(caminho, codificacao)

    with caminho.open("r", encoding=codificacao, newline="") as arquivo:
        linhas = list(csv.reader(arquivo, delimiter=delimitador))

    relatorio = ler_relatorio_cetesb(linhas, caminho)
    if relatorio is not None:
        yield from relatorio
        return

    yield from ler_formato_tabular(caminho, codificacao, delimitador)


def carregar_estacoes(cursor) -> dict[str, tuple[int, str]]:
    cursor.execute("SELECT id, nome FROM estacao_qualidade_ar;")
    return {
        normalizar_texto(nome): (id_estacao, nome)
        for id_estacao, nome in cursor.fetchall()
    }


def gravar_medicao(cursor, id_estacao: int, medicao: Medicao) -> str:
    """Atualiza uma medição existente ou insere uma nova, sem exigir UNIQUE."""
    cursor.execute(
        """
        SELECT id
        FROM medicao_poluente
        WHERE id_estacao = %s
          AND poluente = %s
          AND data_hora = %s
        ORDER BY id
        LIMIT 1;
        """,
        (id_estacao, medicao.poluente, medicao.data_hora),
    )
    existente = cursor.fetchone()

    if existente:
        cursor.execute(
            """
            UPDATE medicao_poluente
               SET valor = %s,
                   unidade = %s
             WHERE id = %s;
            """,
            (medicao.valor, medicao.unidade, existente[0]),
        )
        return "atualizada"

    cursor.execute(
        """
        INSERT INTO medicao_poluente
            (id_estacao, poluente, valor, unidade, data_hora)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (
            id_estacao,
            medicao.poluente,
            medicao.valor,
            medicao.unidade,
            medicao.data_hora,
        ),
    )
    return "inserida"


def importar_arquivo(cursor, caminho: Path, estacoes: dict[str, tuple[int, str]]) -> ResultadoArquivo:
    resultado = ResultadoArquivo(arquivo=caminho)

    try:
        for medicao in ler_medicoes(caminho):
            resultado.lidas += 1
            chave_estacao = normalizar_texto(medicao.estacao)
            dados_estacao = estacoes.get(chave_estacao)
            if not dados_estacao:
                resultado.ignoradas += 1
                print(
                    f"  Aviso: estação {medicao.estacao!r} não existe em "
                    "estacao_qualidade_ar."
                )
                continue

            try:
                situacao = gravar_medicao(cursor, dados_estacao[0], medicao)
                if situacao == "inserida":
                    resultado.inseridas += 1
                else:
                    resultado.atualizadas += 1
            except Exception as erro:
                resultado.erros += 1
                print(
                    f"  Erro ao gravar {medicao.estacao} / {medicao.poluente} / "
                    f"{medicao.data_hora}: {erro}"
                )
                raise
    except Exception:
        raise

    return resultado


def descobrir_arquivos(entradas: list[str]) -> list[Path]:
    caminhos = [Path(item).expanduser() for item in entradas] if entradas else [PASTA_PADRAO]
    arquivos: list[Path] = []

    for caminho in caminhos:
        if caminho.is_dir():
            arquivos.extend(sorted(caminho.glob("*.csv")))
        elif caminho.is_file() and caminho.suffix.lower() == ".csv":
            arquivos.append(caminho)
        else:
            print(f"Aviso: caminho ignorado porque não existe ou não é CSV: {caminho}")

    # Remove duplicações preservando a ordem.
    return list(dict.fromkeys(arquivo.resolve() for arquivo in arquivos))


def importar(arquivos: list[Path]) -> list[ResultadoArquivo]:
    conexao = conectar()
    resultados: list[ResultadoArquivo] = []

    try:
        cursor = conexao.cursor()
        estacoes = carregar_estacoes(cursor)
        if not estacoes:
            raise RuntimeError("Nenhuma estação foi encontrada em estacao_qualidade_ar.")

        for arquivo in arquivos:
            print(f"\nImportando: {arquivo.name}")
            try:
                resultado = importar_arquivo(cursor, arquivo, estacoes)
                conexao.commit()
                resultados.append(resultado)
                print(
                    f"  Concluído: {resultado.inseridas} inseridas, "
                    f"{resultado.atualizadas} atualizadas, "
                    f"{resultado.ignoradas} ignoradas."
                )
            except Exception as erro:
                conexao.rollback()
                resultado = ResultadoArquivo(arquivo=arquivo, erros=1)
                resultados.append(resultado)
                print(f"  Falha no arquivo; alterações desfeitas: {erro}")

        cursor.close()
    finally:
        conexao.close()

    return resultados


def imprimir_resumo(resultados: list[ResultadoArquivo]) -> None:
    print("\n" + "=" * 64)
    print("RESUMO DA IMPORTAÇÃO CETESB")
    print("=" * 64)
    for item in resultados:
        print(
            f"{item.arquivo.name}: "
            f"inseridas={item.inseridas}, atualizadas={item.atualizadas}, "
            f"ignoradas={item.ignoradas}, erros={item.erros}"
        )

    print("-" * 64)
    print(f"Arquivos processados: {len(resultados)}")
    print(f"Registros inseridos: {sum(r.inseridas for r in resultados)}")
    print(f"Registros atualizados: {sum(r.atualizadas for r in resultados)}")
    print(f"Registros ignorados: {sum(r.ignoradas for r in resultados)}")
    print(f"Arquivos com erro: {sum(1 for r in resultados if r.erros)}")
    print("=" * 64)


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa automaticamente arquivos CSV da CETESB para PostgreSQL."
    )
    parser.add_argument(
        "caminhos",
        nargs="*",
        help=(
            "Arquivos CSV ou pastas. Sem argumentos, usa "
            f"'{PASTA_PADRAO.as_posix()}'."
        ),
    )
    return parser


def main() -> int:
    argumentos = criar_parser().parse_args()
    arquivos = descobrir_arquivos(argumentos.caminhos)

    if not arquivos:
        print(
            "Nenhum arquivo CSV encontrado. Coloque os arquivos em "
            f"'{PASTA_PADRAO}' ou informe o caminho na linha de comando."
        )
        return 1

    print(f"Arquivos encontrados: {len(arquivos)}")
    resultados = importar(arquivos)
    imprimir_resumo(resultados)

    return 1 if any(resultado.erros for resultado in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
