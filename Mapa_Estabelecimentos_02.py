import pandas as pd
import geopandas as gpd
import os
import glob
import unicodedata
import folium


def limpar_nome(nome):

    if pd.isna(nome):
        return ""

    nome = str(nome).upper()
    nome = nome.split('(')[0].strip()

    return unicodedata.normalize(
        'NFKD',
        nome
    ).encode(
        'ASCII',
        'ignore'
    ).decode('ASCII')


# =========================================================
# DIRETÓRIO BASE
# =========================================================

base_dir = os.path.dirname(
    os.path.abspath(__file__)
)

# =========================================================
# MALHA IBGE
# =========================================================

caminho_shp = glob.glob(
    os.path.join(
        base_dir,
        "Malha_IBGE",
        "*.shp"
    )
)[0]

geo_goias = gpd.read_file(
    caminho_shp
).to_crs(
    epsg=4326
)

geo_goias["geometry"] = (
    geo_goias["geometry"]
    .simplify(
        tolerance=0.01,
        preserve_topology=True
    )
)

geo_goias["nome_limpo"] = (
    geo_goias["NM_MUN"]
    .apply(limpar_nome)
)

# =========================================================
# ESTABELECIMENTOS
# =========================================================

caminho_excel = os.path.join(
    base_dir,
    "Estabelecimento.xlsx"
)

df_est = pd.read_excel(
    caminho_excel,
    header=None
)

df_est = df_est.iloc[7:].copy()

df_est.columns = [
    "Municipio",
    "Sexo",
    "Nao_Familiar",
    "Familiar"
]

df_est = df_est[
    df_est["Sexo"] == "Total"
].copy()

df_est["Municipio"] = (
    df_est["Municipio"]
    .astype(str)
    .str.replace(
        r"\s*\(GO\)",
        "",
        regex=True
    )
)

df_est["Nao_Familiar"] = pd.to_numeric(
    df_est["Nao_Familiar"],
    errors="coerce"
).fillna(0)

df_est["Familiar"] = pd.to_numeric(
    df_est["Familiar"],
    errors="coerce"
).fillna(0)

df_est["Total"] = (
    df_est["Nao_Familiar"]
    + df_est["Familiar"]
)

df_est["Perc_Familiar"] = (
    df_est["Familiar"]
    / df_est["Total"]
    * 100
)

df_est["nome_limpo"] = (
    df_est["Municipio"]
    .apply(limpar_nome)
)

# =========================================================
# MERGE
# =========================================================

geo_est = geo_goias.merge(
    df_est,
    on="nome_limpo",
    how="left"
)

max_total = geo_est["Total"].max()

# =========================================================
# RANKING
# =========================================================

ranking = (
    geo_est[
        ["NM_MUN", "Total"]
    ]
    .fillna(0)
    .sort_values(
        "Total",
        ascending=False
    )
    .head(10)
)

# =========================================================
# MAPA
# =========================================================

mapa = folium.Map(
    location=[-16.0, -49.0],
    zoom_start=7,
    tiles="cartodbpositron"
)

camadas = [
    ("Total", "Total"),
    ("Familiar", "Familiar"),
    ("Não Familiar", "Nao_Familiar")
]

for nome_camada, coluna in camadas:

    max_valor = geo_est[coluna].max()

    fg = folium.FeatureGroup(
        name=nome_camada,
        show=(coluna == "Total")
    )

    for _, row in geo_est.iterrows():

        valor = row[coluna]

        if pd.isna(valor):
            valor = 0

        popup_html = f"""
        <b>{row['NM_MUN']}</b>

        <hr>

        <b>Familiar:</b>
        {int(row['Familiar']) if pd.notna(row['Familiar']) else 0}

        <br>

        <b>Não Familiar:</b>
        {int(row['Nao_Familiar']) if pd.notna(row['Nao_Familiar']) else 0}

        <hr>

        <b>Total:</b>
        {int(row['Total']) if pd.notna(row['Total']) else 0}

        <br>

        <b>% Familiar:</b>
        {row['Perc_Familiar']:.1f}%
        """

        if valor > max_valor * 0.80:
            cor = "#67000d"

        elif valor > max_valor * 0.60:
            cor = "#a50f15"

        elif valor > max_valor * 0.40:
            cor = "#cb181d"

        elif valor > max_valor * 0.20:
            cor = "#ef3b2c"

        elif valor > 0:
            cor = "#fc9272"

        else:
            cor = "#ffffff"

        folium.GeoJson(

            row["geometry"],

            style_function=lambda x, cor=cor: {
                "fillColor": cor,
                "color": "black",
                "weight": 0.3,
                "fillOpacity": 0.75
            },

            popup=folium.Popup(
                popup_html,
                max_width=300
            )

        ).add_to(fg)

    fg.add_to(mapa)

folium.LayerControl(
    collapsed=False
).add_to(mapa)

# =========================================================
# TÍTULO
# =========================================================

titulo = """
<div style="
position: fixed;
top: 10px;
left: 50%;
transform: translateX(-50%);
z-index:9999;
background:white;
padding:12px 25px;
border-radius:10px;
font-size:24px;
font-weight:bold;
box-shadow:2px 2px 5px rgba(0,0,0,0.3);
">
Estabelecimentos Agropecuários em Goiás
</div>
"""

mapa.get_root().html.add_child(
    folium.Element(titulo)
)

# =========================================================
# RANKING LATERAL
# =========================================================

ranking_html = """
<div style="
position: fixed;
bottom: 20px;
left: 20px;
z-index:9999;
background:white;
padding:15px;
border-radius:8px;
border:1px solid #ccc;
box-shadow:2px 2px 5px rgba(0,0,0,0.3);
width:320px;
">

<h4 style="margin-top:0;">
Top 10 Municípios
</h4>

<table style="width:100%;">
"""

for i, (_, r) in enumerate(
    ranking.iterrows(),
    start=1
):

    ranking_html += f"""
    <tr>
        <td>{i}</td>
        <td>{r['NM_MUN']}</td>
        <td align="right">
            {int(r['Total'])}
        </td>
    </tr>
    """

ranking_html += """
</table>
</div>
"""

mapa.get_root().html.add_child(
    folium.Element(ranking_html)
)

# =========================================================
# LEGENDA
# =========================================================

legenda = """
<div style="
position: fixed;
bottom: 20px;
right: 20px;
z-index:9999;
background:white;
padding:12px;
border-radius:8px;
border:1px solid #ccc;
box-shadow:2px 2px 5px rgba(0,0,0,0.3);
">

<b>Total de Estabelecimentos</b>

<br><br>

<div><span style="background:#67000d;width:20px;height:12px;display:inline-block;"></span> Muito Alto</div>
<div><span style="background:#a50f15;width:20px;height:12px;display:inline-block;"></span> Alto</div>
<div><span style="background:#cb181d;width:20px;height:12px;display:inline-block;"></span> Médio</div>
<div><span style="background:#ef3b2c;width:20px;height:12px;display:inline-block;"></span> Baixo</div>
<div><span style="background:#fc9272;width:20px;height:12px;display:inline-block;"></span> Muito Baixo</div>

</div>
"""

mapa.get_root().html.add_child(
    folium.Element(legenda)
)

# =========================================================
# EXPORTAR
# =========================================================

saida = os.path.join(
    base_dir,
    "mapa_estabelecimentos.html"
)

mapa.save(saida)

print(
    f"Mapa gerado com sucesso: {saida}"
)