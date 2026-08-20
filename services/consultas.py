from __future__ import annotations

from typing import Any

import pandas as pd

from db import conectar
from services.filtros import montar_clausula_filtros


def executar_consulta(
    sql: str,
    parametros: tuple[Any, ...] | None = None,
) -> pd.DataFrame:
    """
    Executa uma consulta SQL no PostgreSQL e devolve o resultado
    como um DataFrame do Pandas.

    Esta função centraliza o acesso ao banco de dados para evitar que
    cada consulta precise repetir o mesmo código de conexão, execução,
    conversão e fechamento.

    Os valores dos filtros são enviados separadamente do texto SQL.
    Essa prática melhora a segurança e evita problemas com aspas,
    caracteres especiais e SQL Injection.
    """

    conexao = None

    try:
        conexao = conectar()

        return pd.read_sql_query(
            sql=sql,
            con=conexao,
            params=parametros,
        )

    except Exception as erro:
        raise RuntimeError(
            f"Erro ao consultar o banco de dados: {erro}"
        ) from erro

    finally:
        # O bloco finally sempre é executado. Assim, a conexão é fechada
        # inclusive quando o PostgreSQL retorna alguma exceção.
        if conexao is not None:
            conexao.close()


def buscar_kpis(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Calcula os principais indicadores exibidos na Home.

    A consulta usa diretamente a View integrada
    vw_fato_mobilidade_poluicao para que todos os indicadores respondam
    aos filtros globais da sidebar.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_posicoes,

            COUNT(
                DISTINCT f.prefixo_veiculo
            ) AS total_veiculos,

            COUNT(
                DISTINCT f.codigo_linha
            ) AS total_linhas,

            COUNT(
                DISTINCT f.regiao
            ) AS total_regioes,

            ROUND(
                AVG(f.distancia_metros),
                2
            ) AS distancia_media,

            ROUND(
                MAX(f.distancia_metros),
                2
            ) AS maior_distancia,

            COUNT(f.mp10) AS registros_com_mp10,
            COUNT(f.mp25) AS registros_com_mp25,
            COUNT(f.no) AS registros_com_no,
            COUNT(f.no2) AS registros_com_no2,

            COUNT(*) FILTER (
                WHERE
                    f.mp10 IS NOT NULL
                    OR f.mp25 IS NOT NULL
                    OR f.no IS NOT NULL
                    OR f.no2 IS NOT NULL
            ) AS registros_com_dados_ambientais,

            ROUND(
                (
                    COUNT(*) FILTER (
                        WHERE
                            f.mp10 IS NOT NULL
                            OR f.mp25 IS NOT NULL
                            OR f.no IS NOT NULL
                            OR f.no2 IS NOT NULL
                    )
                )::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_ambiental_percentual

        FROM vw_fato_mobilidade_poluicao AS f

        {where};
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_resumo_regioes(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Agrupa as coletas por região.

    O resultado alimenta:
    - gráfico de coletas por região;
    - gráfico de médias dos poluentes;
    - tabela comparativa da Home.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            f.regiao,

            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.prefixo_veiculo
            ) AS total_veiculos,

            COUNT(
                DISTINCT f.codigo_linha
            ) AS total_linhas,

            ROUND(
                AVG(f.distancia_metros),
                2
            ) AS distancia_media,

            ROUND(AVG(f.mp10), 2) AS mp10,
            ROUND(AVG(f.mp25), 2) AS mp25,
            ROUND(AVG(f.no), 2) AS no,
            ROUND(AVG(f.no2), 2) AS no2

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        GROUP BY
            f.regiao

        ORDER BY
            total_coletas DESC,
            f.regiao;
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_fluxo_linhas(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
    limite: int = 10,
) -> pd.DataFrame:
    """
    Retorna as linhas com maior quantidade de coletas.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            f.codigo_linha,

            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.prefixo_veiculo
            ) AS total_veiculos,

            ROUND(
                AVG(f.distancia_metros),
                2
            ) AS distancia_media

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        GROUP BY
            f.codigo_linha

        ORDER BY
            total_coletas DESC,
            f.codigo_linha

        LIMIT %s;
    """

    parametros_com_limite = [*parametros, limite]

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros_com_limite),
    )


def buscar_distribuicao_distancias(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Agrupa as coletas pelas faixas de distância entre ônibus e estação.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        WITH distribuicao AS (
            SELECT
                COALESCE(
                    f.faixa_distancia,
                    'Não classificada'
                ) AS faixa_distancia,

                COUNT(*) AS total_coletas

            FROM vw_fato_mobilidade_poluicao AS f

            {where}

            GROUP BY
                COALESCE(
                    f.faixa_distancia,
                    'Não classificada'
                )
        )

        SELECT
            faixa_distancia,
            total_coletas,

            ROUND(
                total_coletas::numeric
                / NULLIF(
                    SUM(total_coletas) OVER (),
                    0
                )
                * 100,
                2
            ) AS percentual

        FROM distribuicao

        ORDER BY
            CASE faixa_distancia
                WHEN 'Até 1 km' THEN 1
                WHEN '1 a 3 km' THEN 2
                WHEN '1–3 km' THEN 2
                WHEN '1 - 3 km' THEN 2
                WHEN '3 a 5 km' THEN 3
                WHEN '3–5 km' THEN 3
                WHEN '3 - 5 km' THEN 3
                WHEN '5 a 10 km' THEN 4
                WHEN '5–10 km' THEN 4
                WHEN '5 - 10 km' THEN 4
                WHEN 'Acima de 10 km' THEN 5
                WHEN 'Mais de 10 km' THEN 5
                ELSE 6
            END,
            faixa_distancia;
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_insights_dashboard(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Calcula os principais destaques do recorte selecionado.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        WITH dados_filtrados AS (
            SELECT
                f.regiao,
                f.codigo_linha,
                f.estacao,
                f.distancia_metros

            FROM vw_fato_mobilidade_poluicao AS f

            {where}
        ),

        fluxo_regiao AS (
            SELECT
                regiao,
                COUNT(*) AS total_coletas

            FROM dados_filtrados

            WHERE regiao IS NOT NULL

            GROUP BY regiao

            ORDER BY
                total_coletas DESC,
                regiao

            LIMIT 1
        ),

        fluxo_linha AS (
            SELECT
                codigo_linha,
                COUNT(*) AS total_coletas

            FROM dados_filtrados

            WHERE codigo_linha IS NOT NULL

            GROUP BY codigo_linha

            ORDER BY
                total_coletas DESC,
                codigo_linha

            LIMIT 1
        ),

        fluxo_estacao AS (
            SELECT
                estacao,
                COUNT(*) AS total_coletas

            FROM dados_filtrados

            WHERE estacao IS NOT NULL

            GROUP BY estacao

            ORDER BY
                total_coletas DESC,
                estacao

            LIMIT 1
        ),

        resumo_distancias AS (
            SELECT
                ROUND(
                    AVG(distancia_metros),
                    2
                ) AS distancia_media,

                ROUND(
                    MAX(distancia_metros),
                    2
                ) AS maior_distancia

            FROM dados_filtrados
        )

        SELECT
            (
                SELECT regiao
                FROM fluxo_regiao
            ) AS regiao_maior_fluxo,

            (
                SELECT total_coletas
                FROM fluxo_regiao
            ) AS total_regiao_maior_fluxo,

            (
                SELECT codigo_linha
                FROM fluxo_linha
            ) AS linha_mais_observada,

            (
                SELECT total_coletas
                FROM fluxo_linha
            ) AS total_linha_mais_observada,

            (
                SELECT estacao
                FROM fluxo_estacao
            ) AS estacao_mais_utilizada,

            (
                SELECT total_coletas
                FROM fluxo_estacao
            ) AS total_estacao_mais_utilizada,

            resumo_distancias.distancia_media,
            resumo_distancias.maior_distancia

        FROM resumo_distancias;
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


# ----------------------------------------------------------------------
# CONSULTAS ESPECÍFICAS DA PÁGINA DE QUALIDADE DO AR
# ----------------------------------------------------------------------


def buscar_kpis_qualidade_ar(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Calcula os indicadores ambientais do recorte selecionado.

    A função retorna uma única linha contendo:
    - médias de MP10, MP2.5, NO e NO2;
    - máximos observados;
    - total de estações associadas;
    - total de coletas;
    - total de coletas com algum dado ambiental;
    - cobertura geral e cobertura individual por poluente.

    A cobertura individual informa em qual proporção das coletas cada
    poluente estava disponível. Isso é importante porque a média de um
    poluente pode ter sido calculada com menos observações que outro.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.estacao
            ) AS total_estacoes,

            ROUND(AVG(f.mp10), 2) AS media_mp10,
            ROUND(AVG(f.mp25), 2) AS media_mp25,
            ROUND(AVG(f.no), 2) AS media_no,
            ROUND(AVG(f.no2), 2) AS media_no2,

            ROUND(MAX(f.mp10), 2) AS maximo_mp10,
            ROUND(MAX(f.mp25), 2) AS maximo_mp25,
            ROUND(MAX(f.no), 2) AS maximo_no,
            ROUND(MAX(f.no2), 2) AS maximo_no2,

            COUNT(*) FILTER (
                WHERE
                    f.mp10 IS NOT NULL
                    OR f.mp25 IS NOT NULL
                    OR f.no IS NOT NULL
                    OR f.no2 IS NOT NULL
            ) AS coletas_com_dados_ambientais,

            ROUND(
                (
                    COUNT(*) FILTER (
                        WHERE
                            f.mp10 IS NOT NULL
                            OR f.mp25 IS NOT NULL
                            OR f.no IS NOT NULL
                            OR f.no2 IS NOT NULL
                    )
                )::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_ambiental_percentual,

            ROUND(
                COUNT(f.mp10)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_mp10_percentual,

            ROUND(
                COUNT(f.mp25)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_mp25_percentual,

            ROUND(
                COUNT(f.no)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_no_percentual,

            ROUND(
                COUNT(f.no2)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_no2_percentual

        FROM vw_fato_mobilidade_poluicao AS f

        {where};
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_poluentes_por_linha(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
    limite: int = 15,
) -> pd.DataFrame:
    """
    Compara as médias dos poluentes entre as linhas de ônibus.

    A consulta também devolve:
    - quantidade de coletas;
    - veículos distintos;
    - estações associadas;
    - distância média;
    - cobertura ambiental da linha.

    A presença de cobertura e distância média ajuda a interpretar os
    resultados com cautela. Uma linha com poucas coletas ou associação
    espacial distante não deve ser comparada de forma simplista.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            f.codigo_linha,

            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.prefixo_veiculo
            ) AS total_veiculos,

            COUNT(
                DISTINCT f.estacao
            ) AS total_estacoes,

            ROUND(
                AVG(f.distancia_metros),
                2
            ) AS distancia_media,

            ROUND(AVG(f.mp10), 2) AS media_mp10,
            ROUND(AVG(f.mp25), 2) AS media_mp25,
            ROUND(AVG(f.no), 2) AS media_no,
            ROUND(AVG(f.no2), 2) AS media_no2,

            ROUND(
                (
                    COUNT(*) FILTER (
                        WHERE
                            f.mp10 IS NOT NULL
                            OR f.mp25 IS NOT NULL
                            OR f.no IS NOT NULL
                            OR f.no2 IS NOT NULL
                    )
                )::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_ambiental_percentual

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        GROUP BY
            f.codigo_linha

        ORDER BY
            total_coletas DESC,
            f.codigo_linha

        LIMIT %s;
    """

    parametros_com_limite = [*parametros, limite]

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros_com_limite),
    )


def buscar_poluentes_por_distancia(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Compara os poluentes entre as faixas de distância.

    Esta análise não prova que a distância provoca alteração na poluição.
    Ela mostra apenas como os valores ambientais associados às posições
    dos ônibus se distribuem conforme a proximidade da estação.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            COALESCE(
                f.faixa_distancia,
                'Não classificada'
            ) AS faixa_distancia,

            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.estacao
            ) AS total_estacoes,

            ROUND(
                AVG(f.distancia_metros),
                2
            ) AS distancia_media,

            ROUND(AVG(f.mp10), 2) AS media_mp10,
            ROUND(AVG(f.mp25), 2) AS media_mp25,
            ROUND(AVG(f.no), 2) AS media_no,
            ROUND(AVG(f.no2), 2) AS media_no2,

            ROUND(
                (
                    COUNT(*) FILTER (
                        WHERE
                            f.mp10 IS NOT NULL
                            OR f.mp25 IS NOT NULL
                            OR f.no IS NOT NULL
                            OR f.no2 IS NOT NULL
                    )
                )::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_ambiental_percentual

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        GROUP BY
            COALESCE(
                f.faixa_distancia,
                'Não classificada'
            )

        ORDER BY
            CASE COALESCE(
                f.faixa_distancia,
                'Não classificada'
            )
                WHEN 'Até 1 km' THEN 1
                WHEN '1 a 3 km' THEN 2
                WHEN '1–3 km' THEN 2
                WHEN '1 - 3 km' THEN 2
                WHEN '3 a 5 km' THEN 3
                WHEN '3–5 km' THEN 3
                WHEN '3 - 5 km' THEN 3
                WHEN '5 a 10 km' THEN 4
                WHEN '5–10 km' THEN 4
                WHEN '5 - 10 km' THEN 4
                WHEN 'Acima de 10 km' THEN 5
                WHEN 'Mais de 10 km' THEN 5
                ELSE 6
            END;
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_cobertura_por_linha(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
    limite: int = 15,
) -> pd.DataFrame:
    """
    Mede a disponibilidade de dados ambientais por linha.

    A consulta separa:
    - cobertura geral;
    - cobertura de MP10;
    - cobertura de MP2.5;
    - cobertura de NO;
    - cobertura de NO2.

    Essa visão ajuda a identificar comparações potencialmente frágeis.
    Uma linha com cobertura baixa pode apresentar uma média baseada em
    poucas observações ambientais.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            f.codigo_linha,

            COUNT(*) AS total_coletas,

            COUNT(
                DISTINCT f.prefixo_veiculo
            ) AS total_veiculos,

            ROUND(
                (
                    COUNT(*) FILTER (
                        WHERE
                            f.mp10 IS NOT NULL
                            OR f.mp25 IS NOT NULL
                            OR f.no IS NOT NULL
                            OR f.no2 IS NOT NULL
                    )
                )::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_ambiental_percentual,

            ROUND(
                COUNT(f.mp10)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_mp10_percentual,

            ROUND(
                COUNT(f.mp25)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_mp25_percentual,

            ROUND(
                COUNT(f.no)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_no_percentual,

            ROUND(
                COUNT(f.no2)::numeric
                / NULLIF(COUNT(*), 0)
                * 100,
                2
            ) AS cobertura_no2_percentual

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        GROUP BY
            f.codigo_linha

        ORDER BY
            total_coletas DESC,
            f.codigo_linha

        LIMIT %s;
    """

    parametros_com_limite = [*parametros, limite]

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros_com_limite),
    )


def buscar_detalhes_qualidade_ar(
    regioes=None,
    linhas=None,
    veiculos=None,
    janelas=None,
    data_inicial=None,
    data_final=None,
    limite: int = 1000,
) -> pd.DataFrame:
    """
    Retorna os registros detalhados da relação entre transporte e ar.

    Essa consulta alimenta a tabela da página Qualidade do Ar. O limite
    evita carregar uma quantidade excessiva de linhas no navegador.

    Os dados são ordenados do registro mais recente para o mais antigo.
    """

    where, parametros = montar_clausula_filtros(
        alias="f",
        regioes=regioes,
        linhas=linhas,
        veiculos=veiculos,
        janelas=janelas,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    sql = f"""
        SELECT
            f.data_hora_coleta,
            f.regiao,
            f.codigo_linha,
            f.prefixo_veiculo,
            f.estacao,
            f.janela_coleta,
            f.distancia_metros,
            f.faixa_distancia,
            f.mp10,
            f.mp25,
            f.no,
            f.no2

        FROM vw_fato_mobilidade_poluicao AS f

        {where}

        ORDER BY
            f.data_hora_coleta DESC,
            f.codigo_linha,
            f.prefixo_veiculo

        LIMIT %s;
    """

    parametros_com_limite = [*parametros, limite]

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros_com_limite),
    )


def buscar_opcoes_mapa() -> pd.DataFrame:
    """
    Retorna as opções básicas utilizadas pelos filtros locais do mapa.
    """

    sql = """
        SELECT
            ARRAY_AGG(
                DISTINCT regiao
                ORDER BY regiao
            ) AS regioes,

            ARRAY_AGG(
                DISTINCT codigo_linha
                ORDER BY codigo_linha
            ) AS linhas,

            MIN(data_hora_coleta)::date AS data_inicial,
            MAX(data_hora_coleta)::date AS data_final

        FROM vw_fato_mobilidade_poluicao;
    """

    return executar_consulta(sql)


def buscar_dados_mapa(
    regioes=None,
    linhas=None,
    data_inicial=None,
    data_final=None,
) -> pd.DataFrame:
    """
    Busca os registros espaciais exibidos no mapa interativo.
    """

    filtros = []
    parametros = []

    if regioes:
        filtros.append("f.regiao = ANY(%s)")
        parametros.append(regioes)

    if linhas:
        filtros.append("f.codigo_linha = ANY(%s)")
        parametros.append(linhas)

    if data_inicial:
        filtros.append("f.data_hora_coleta >= %s")
        parametros.append(data_inicial)

    if data_final:
        filtros.append(
            "f.data_hora_coleta < (%s::date + INTERVAL '1 day')"
        )
        parametros.append(data_final)

    clausula_where = ""

    if filtros:
        clausula_where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT
            f.id_coleta,
            f.prefixo_veiculo,
            f.codigo_linha,
            f.regiao,
            f.estacao,
            f.latitude AS latitude_onibus,
            f.longitude AS longitude_onibus,
            f.distancia_metros,
            f.faixa_distancia,
            f.janela_coleta,
            f.data_hora_coleta,
            f.mp10,
            f.mp25,
            f.no,
            f.no2,
            e.latitude AS latitude_estacao,
            e.longitude AS longitude_estacao

        FROM vw_fato_mobilidade_poluicao AS f

        JOIN estacao_qualidade_ar AS e
            ON e.nome = f.estacao

        {clausula_where}

        ORDER BY
            f.data_hora_coleta DESC,
            f.id_coleta

        LIMIT 500;
    """

    return executar_consulta(
        sql=sql,
        parametros=tuple(parametros),
    )


def buscar_estacoes_mapa() -> pd.DataFrame:
    """
    Retorna as estações ambientais cadastradas e suas coordenadas.
    """

    sql = """
        SELECT
            e.id,
            e.nome AS estacao,
            r.nome AS regiao,
            e.latitude,
            e.longitude

        FROM estacao_qualidade_ar AS e

        JOIN regiao AS r
            ON r.id = e.id_regiao

        ORDER BY
            e.nome;
    """

    return executar_consulta(sql)


def buscar_opcoes_filtros() -> pd.DataFrame:
    """
    Retorna as opções utilizadas pela sidebar global.
    """

    sql = """
        SELECT
            ARRAY_AGG(
                DISTINCT regiao
                ORDER BY regiao
            ) AS regioes,

            ARRAY_AGG(
                DISTINCT codigo_linha
                ORDER BY codigo_linha
            ) AS linhas,

            ARRAY_AGG(
                DISTINCT prefixo_veiculo
                ORDER BY prefixo_veiculo
            ) AS veiculos,

            ARRAY_AGG(
                DISTINCT janela_coleta
                ORDER BY janela_coleta
            ) FILTER (
                WHERE janela_coleta IS NOT NULL
            ) AS janelas,

            MIN(data_hora_coleta)::date AS data_inicial,
            MAX(data_hora_coleta)::date AS data_final

        FROM vw_fato_mobilidade_poluicao;
    """

    return executar_consulta(sql)
