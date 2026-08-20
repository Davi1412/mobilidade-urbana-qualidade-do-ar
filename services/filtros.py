from __future__ import annotations

from datetime import date
from typing import Any


def montar_clausula_filtros(
    alias: str = "f",
    regioes: list[str] | None = None,
    linhas: list[str] | None = None,
    veiculos: list[str] | None = None,
    janelas: list[str] | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
) -> tuple[str, list[Any]]:
    """
    Monta dinamicamente a cláusula WHERE e seus parâmetros.

    O alias representa o nome utilizado para a tabela ou View na consulta.
    """

    condicoes: list[str] = []
    parametros: list[Any] = []

    if regioes:
        condicoes.append(f"{alias}.regiao = ANY(%s)")
        parametros.append(regioes)

    if linhas:
        condicoes.append(f"{alias}.codigo_linha = ANY(%s)")
        parametros.append(linhas)

    if veiculos:
        condicoes.append(f"{alias}.prefixo_veiculo = ANY(%s)")
        parametros.append(veiculos)

    if janelas:
        condicoes.append(f"{alias}.janela_coleta = ANY(%s)")
        parametros.append(janelas)

    if data_inicial:
        condicoes.append(f"{alias}.data_hora_coleta >= %s")
        parametros.append(data_inicial)

    if data_final:
        condicoes.append(
            f"{alias}.data_hora_coleta < (%s::date + INTERVAL '1 day')"
        )
        parametros.append(data_final)

    if not condicoes:
        return "", parametros

    return "WHERE " + " AND ".join(condicoes), parametros