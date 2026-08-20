from __future__ import annotations

import math

import folium
import pandas as pd
from folium.plugins import MarkerCluster


def _valor_texto(valor, casas: int = 2) -> str:
    if pd.isna(valor):
        return "Indisponível"
    return f"{float(valor):.{casas}f}"


def criar_mapa(
    dados_onibus: pd.DataFrame,
    dados_estacoes: pd.DataFrame,
    mostrar_ligacoes: bool = True,
    agrupar_onibus: bool = True,
) -> folium.Map:
    """
    Cria mapa Folium com ônibus, estações CETESB e ligações espaciais.
    """

    if dados_onibus.empty and dados_estacoes.empty:
        return folium.Map(
            location=[-23.5505, -46.6333],
            zoom_start=11,
            control_scale=True,
        )

    latitudes = []
    longitudes = []

    if not dados_onibus.empty:
        latitudes.extend(dados_onibus["latitude_onibus"].dropna().tolist())
        longitudes.extend(dados_onibus["longitude_onibus"].dropna().tolist())

    if not dados_estacoes.empty:
        latitudes.extend(dados_estacoes["latitude"].dropna().tolist())
        longitudes.extend(dados_estacoes["longitude"].dropna().tolist())

    centro_lat = sum(latitudes) / len(latitudes) if latitudes else -23.5505
    centro_lon = sum(longitudes) / len(longitudes) if longitudes else -46.6333

    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=11,
        control_scale=True,
        tiles="CartoDB positron",
    )

    camada_estacoes = folium.FeatureGroup(
        name="Estações CETESB",
        show=True,
    )

    for _, estacao in dados_estacoes.iterrows():
        popup = folium.Popup(
            f"""
            <div style="min-width:220px">
                <h4 style="margin-bottom:8px">Estação CETESB</h4>
                <b>Nome:</b> {estacao['estacao']}<br>
                <b>Região:</b> {estacao['regiao']}<br>
                <b>Latitude:</b> {estacao['latitude']:.6f}<br>
                <b>Longitude:</b> {estacao['longitude']:.6f}
            </div>
            """,
            max_width=320,
        )

        folium.Marker(
            location=[estacao["latitude"], estacao["longitude"]],
            tooltip=f"Estação: {estacao['estacao']}",
            popup=popup,
            icon=folium.Icon(
                color="green",
                icon="cloud",
                prefix="fa",
            ),
        ).add_to(camada_estacoes)

    camada_estacoes.add_to(mapa)

    camada_onibus = folium.FeatureGroup(
        name="Ônibus",
        show=True,
    )

    destino_onibus = (
        MarkerCluster(name="Agrupamento de ônibus")
        if agrupar_onibus
        else camada_onibus
    )

    for _, linha in dados_onibus.iterrows():
        if pd.isna(linha["latitude_onibus"]) or pd.isna(linha["longitude_onibus"]):
            continue

        distancia = _valor_texto(linha["distancia_metros"])
        data_hora = pd.to_datetime(linha["data_hora_coleta"]).strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        popup = folium.Popup(
            f"""
            <div style="min-width:260px">
                <h4 style="margin-bottom:8px">Ônibus {linha['prefixo_veiculo']}</h4>
                <b>Linha:</b> {linha['codigo_linha']}<br>
                <b>Região:</b> {linha['regiao']}<br>
                <b>Estação associada:</b> {linha['estacao']}<br>
                <b>Distância:</b> {distancia} m<br>
                <b>Faixa:</b> {linha['faixa_distancia']}<br>
                <b>Janela:</b> {linha['janela_coleta']}<br>
                <b>Coleta:</b> {data_hora}<hr>
                <b>MP10:</b> {_valor_texto(linha['mp10'])}<br>
                <b>MP2.5:</b> {_valor_texto(linha['mp25'])}<br>
                <b>NO:</b> {_valor_texto(linha['no'])}<br>
                <b>NO2:</b> {_valor_texto(linha['no2'])}
            </div>
            """,
            max_width=360,
        )

        folium.CircleMarker(
            location=[linha["latitude_onibus"], linha["longitude_onibus"]],
            radius=6,
            tooltip=(
                f"Ônibus {linha['prefixo_veiculo']} | "
                f"Linha {linha['codigo_linha']}"
            ),
            popup=popup,
            color="#1565c0",
            fill=True,
            fill_color="#1976d2",
            fill_opacity=0.85,
            weight=2,
        ).add_to(destino_onibus)

        if (
            mostrar_ligacoes
            and not pd.isna(linha["latitude_estacao"])
            and not pd.isna(linha["longitude_estacao"])
        ):
            folium.PolyLine(
                locations=[
                    [linha["latitude_onibus"], linha["longitude_onibus"]],
                    [linha["latitude_estacao"], linha["longitude_estacao"]],
                ],
                color="#757575",
                weight=1.2,
                opacity=0.45,
                tooltip=f"Distância: {distancia} m",
            ).add_to(mapa)

    if agrupar_onibus:
        destino_onibus.add_to(mapa)
    else:
        camada_onibus.add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    if latitudes and longitudes:
        mapa.fit_bounds(
            [
                [min(latitudes), min(longitudes)],
                [max(latitudes), max(longitudes)],
            ],
            padding=(20, 20),
        )

    return mapa
