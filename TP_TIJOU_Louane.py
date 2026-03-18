# %% [markdown]
# 1) Import des Packages

# %%
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import calendar as calendar
import dash
from dash import html, dcc, dash_table, Input, Output


# %% [markdown]
# 2)  Charger et préparer les données

# %%
# 1. Chargement des données
df = pd.read_csv("data.csv")
df = df.iloc[:52923]
# df.info()
# Chaque ligne représente une vente 

# Garder seulement les colonnes utiles pour l'analyse
colonnes_utiles = ['CustomerID', 'Gender', 'Location', 'Product_Category','Quantity', 'Avg_Price', 'Transaction_Date','Month', 'Discount_pct']
df = df[colonnes_utiles]
# df.info()

# Remplacer les valeurs manquantes dans `CustomerID` par 0 et convertir `CustomerID` en entier.
df['CustomerID'] = df['CustomerID'].fillna(0).astype(int)

# Convertir `Transaction_Date` en date.
df['Transaction_Date'] = pd.to_datetime(df['Transaction_Date'])

# Créer `Total_price` avec la remise.
df["Total_price"] = df["Quantity"] * df["Avg_Price"] * (1 - df["Discount_pct"] / 100)


print(df.head()) 
print("\n")
print(df.dtypes)
print("\n")
print(df['Total_price'].describe()) 


# %% [markdown]
# 3) Écrire les fonctions métier

# %%
# calculer_chiffre_affaire(data)

def calculer_chiffre_affaire(data):
    chiffre_affaire = data["Total_price"].sum()
    return chiffre_affaire

# frequence_meilleure_vente(data, top=10, ascending=False)

def frequence_meilleure_vente(data, top=10, ascending=False):
    freq = data["Product_Category"].value_counts(ascending=ascending)
    return freq.head(top)


# %%
def indicateur_du_mois(data, month=12, freq=True, year=None, unite='k'):
    
    data = data.copy()  

    data["Transaction_Date"] = pd.to_datetime(data["Transaction_Date"])

    if year is None:
        year = data["Transaction_Date"].dt.year.max()

    df_current = data[
        (data["Transaction_Date"].dt.month == month) &
        (data["Transaction_Date"].dt.year == year)]

    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year

    df_prev = data[
        (data["Transaction_Date"].dt.month == prev_month) &
        (data["Transaction_Date"].dt.year == prev_year)]

    if freq:
        val_current = df_current.shape[0]
        difference = val_current - df_prev.shape[0]
        suffixe = ""
    else:
        val_current = df_current["Total_price"].sum()
        difference = val_current - df_prev["Total_price"].sum()

        if unite == 'k':
            val_current = int(round(val_current / 1000, 0))
            difference = int(round(difference / 1000, 0))
            suffixe = "k"
        else:
            suffixe = ""

    color = "#2e7d32" if difference >= 0 else "#d32f2f"
    arrow = "▲" if difference >= 0 else "▼"
    diff_sign = "+" if difference > 0 else ""
    nom_mois = calendar.month_name[month]

    return html.Div(
        style={
            "display": "inline-block",
            "textAlign": "center",
            "fontFamily": "sans-serif",
            "margin": "20px",
            "minWidth": "150px"
        },
        children=[
            html.Div(nom_mois, style={"color": "#4a5568", "fontSize": "16px", "marginBottom": "8px"}),
            html.Div(f"{val_current}{suffixe}", style={
                "color": "#2d3748",
                "fontSize": "48px",
                "fontWeight": "bold",
                "lineHeight": "1"
            }),
            html.Div(f"{arrow} {diff_sign}{difference}{suffixe}", style={
                "color": color,
                "fontSize": "24px",
                "marginTop": "8px"
            })
        ]
    )

# %% [markdown]
# 4) Créer les graphiques

# %%
def plot_evolution_chiffre_affaire(df):

    df = df.copy()  
    df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"])
    
    # Par semaine
    df_ca = df.groupby(pd.Grouper(key="Transaction_Date", freq='W'))["Total_price"].sum().reset_index()

    # Bornes
    y_min = df_ca["Total_price"].min()
    y_max = df_ca["Total_price"].max()

    marge = (y_max - y_min) * 0.1 if y_max != y_min else 1000

    y_min = max(0, y_min - marge)
    y_max = y_max + marge

    y_range = y_max - y_min
    if y_range > 50000:
        dtick = 10000  # 10k
    else:
        dtick = round(y_range / 5, -3)  

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_ca["Transaction_Date"],
        y=df_ca["Total_price"],
        mode='lines',
        line=dict(color='royalblue', width=3),
        name="Chiffre d'affaires"
    ))

    fig.update_layout(
        title="Évolution du chiffre d'affaires par semaine",
        xaxis_title="Semaine",
        yaxis_title="Chiffre d'affaires",
        plot_bgcolor='#e5ecf6',
        paper_bgcolor='white',
        xaxis=dict(
            tickformat="%b %Y",
            dtick="M2",
            showgrid=True,
            gridcolor='white'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='white',
            range=[y_min, y_max],
            dtick=dtick 
        ),
        template='plotly_white')

    return fig



# %%
def create_df_table(df):
    df_table = df[[
        "Transaction_Date",
        "Gender",
        "Location",
        "Product_Category",
        "Quantity",
        "Avg_Price",
        "Discount_pct"
    ]].rename(columns={
        "Transaction_Date": "Date",
        "Gender": "Genre",
        "Location": "Location",
        "Product_Category": "Product Category",
        "Quantity": "Quantity",
        "Avg_Price": "Average Price",
        "Discount_pct": "Discount (%)"
    })
    
    df_table = df_table.sort_values("Date", ascending=False).head(100)

    df_table["Date"] = pd.to_datetime(df_table["Date"]).dt.date.astype(str)

    return df_table


# %%
def barplot_top_10_ventes(data, month=12, year=None, abbr=False):
    """
    Barplot horizontal des 10 catégories les plus vendues par sexe,
    basé sur le nombre de commandes (lignes) pour le mois choisi.
    """

    data["Transaction_Date"] = pd.to_datetime(data["Transaction_Date"])

    df_filtered = data[data["Transaction_Date"].dt.month == month]
    if year is not None:
        df_filtered = df_filtered[df_filtered["Transaction_Date"].dt.year == year]

    # Nombre de commandes par catégorie et sexe
    df_grouped = df_filtered.groupby(["Product_Category", "Gender"]).size().unstack(fill_value=0)

    # Top 10 catégories
    top_10_cat = df_grouped.sum(axis=1).sort_values(ascending=False).head(10).index.tolist()
    df_grouped = df_grouped.loc[top_10_cat]

    # Trier 
    df_grouped = df_grouped.sort_values(by=df_grouped.columns.tolist(), ascending=True)

    # Nom du mois
    nom_mois = calendar.month_abbr[month] if abbr else calendar.month_name[month]
    titre = f"Frequence des 10 meilleures ventes - {nom_mois}"

    fig = go.Figure()

    # Femmes 
    if "F" in df_grouped.columns:
        fig.add_trace(go.Bar(
            y=df_grouped.index,
            x=df_grouped["F"],
            name="F",
            orientation='h',
            marker_color='steelblue'))

    # Hommes 
    if "M" in df_grouped.columns:
        fig.add_trace(go.Bar(
            y=df_grouped.index,
            x=df_grouped["M"],
            name="M",
            orientation='h',
            marker_color='indianred' ))

    fig.update_layout(
        barmode='group',
        title={
            'text': titre,
            'font': {'size': 14},
            'x': 0.5
        },
        xaxis_title="Total vente",
        yaxis_title="Categorie du produit",
        template='plotly_white',
        yaxis={'categoryorder': 'array', 'categoryarray': df_grouped.index})

    return fig

# %% [markdown]
# 5. Application Dash 

# %%
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([

    # HEADER
    html.Div(
        style={"background": "#b3d7f2", "padding": "12px 20px", "display": "flex", "alignItems": "center"},
        children=[
            html.Div("ECAP Store", style={"fontSize": "24px", "fontWeight": "700", "flex": "1"}),
            dcc.Dropdown(
                id="dropdown-location",
                options=[{"label": "Toutes", "value": "Toutes"}] +
                        [{"label": loc, "value": loc} for loc in sorted(df["Location"].unique())],
                value="Toutes",
                placeholder="Choisissez des zones",
                style={"width": "260px"}
            )
        ]
    ),

    # ORGANISATION PRINCIPALE
    html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "40% 60%",
            "gap": "20px",
            "padding": "20px"
        },
        children=[

            # COLONNE GAUCHE
            html.Div(
                style={"display": "flex", "flexDirection": "column", "gap": "20px"},
                children=[

                    html.Div(
                        style={"display": "flex", "gap": "16px"},
                        children=[
                            html.Div(id="kpi-ca"),
                            html.Div(id="kpi-freq"),
                        ]
                    ),

                    dcc.Graph(
                        id="graph-top10",
                        figure=barplot_top_10_ventes(df, month=12),
                        style={"height": "520px", "width": "100%"}
                    )
                ]
            ),

            # COLONNE DROITE
            html.Div(
                style={"display": "flex", "flexDirection": "column", "gap": "20px", "height": "100%"},
                children=[
                    html.Div(
                        style={"height": "42%"},
                        children=[
                            dcc.Graph(
                                id="graph-evolution",
                                figure=plot_evolution_chiffre_affaire(df),
                                style={"height": "110%", "width": "108%"}
                            )
                        ]
                    ),
                    html.Div(
                        style={"height": "50%"},
                        children=[
                            html.H3("Table des 100 dernières ventes", style={"marginBottom": "8px","fontSize": "18px"}),
                            dash_table.DataTable(
                                id="table-ventes",
                                columns=[{"name": c, "id": c} for c in create_df_table(df).columns],
                                data=create_df_table(df).to_dict("records"),
                                filter_action="native",
                                sort_action="native",
                                page_action="native", 
                                page_size=8,
                                style_table={"overflowY": "auto", "height": "85%"},
                                style_cell={"textAlign": "left", "padding": "6px","fontSize": "11px"},
                                style_header={"backgroundColor": "#f4f6f8", "fontWeight": "bold","padding": "6px"}
                            )
                        ]
                    )
                ]
            )
        ]
    )
])

@app.callback(
    Output("graph-top10", "figure"),
    Output("graph-evolution", "figure"),
    Output("table-ventes", "data"),
    Output("kpi-ca", "children"),      
    Output("kpi-freq", "children"),    
    Input("dropdown-location", "value")
)

def update_graphs(location):

    if not location or location == "Toutes":
        dff = df.copy()
    else:
        dff = df[df["Location"] == location].copy()

    # Graphs
    fig_top10 = barplot_top_10_ventes(dff, month=12)
    fig_evol = plot_evolution_chiffre_affaire(dff)
    table_data = create_df_table(dff).to_dict("records")


    kpi_ca = indicateur_du_mois(dff, month=12, freq=False)
    kpi_freq = indicateur_du_mois(dff, month=12, freq=True)

    return fig_top10, fig_evol, table_data, kpi_ca, kpi_freq


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)


