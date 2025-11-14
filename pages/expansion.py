import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import utils.db as db
st.write("Funciones disponibles:", dir(db))
from utils.db import run_query, run_cached_query

import os

# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(page_title="Panel de Expansión", layout="wide")


# ==========================================================
# LOGO Y TÍTULO
# ==========================================================
logo_path = os.path.join("logo", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=120)

st.title("Panel de Expansión - Oportunidades de Crecimiento")

# ==========================================================
# TABS PRINCIPALES
# ==========================================================
tab1, tab2 = st.tabs(["📊 Análisis Territorial", "🧠 Recomendador de Nuevas Tiendas"])


# ==========================================================
# TAB 1 - ANÁLISIS TERRITORIAL
# ==========================================================
with tab1:
    st.subheader("Filtros de análisis")
    nivel = st.selectbox("Nivel de análisis", ["Región", "Ciudad", "Pueblo (Town)"], index=0)

    st.divider()

    # ------------------------------------------------------
    # CONSULTAS SQL (pesadas → cacheadas)
    # ------------------------------------------------------
    if nivel == "Región":
        query_gasto = """
        SELECT 
            b."REGION" AS nivel,
            SUM(o."TOTALBASKET") AS total_ventas,
            COUNT(DISTINCT b."BRANCH_ID") AS num_tiendas,
            COUNT(DISTINCT o."USERID") AS num_clientes,
            SUM(o."TOTALBASKET") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS ventas_por_tienda,
            COUNT(DISTINCT o."USERID") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS clientes_por_tienda
        FROM "Orders" o
        JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
        GROUP BY b."REGION"
        ORDER BY ventas_por_tienda DESC;
        """
    elif nivel == "Ciudad":
        query_gasto = """
        SELECT 
            b."CITY" AS nivel,
            SUM(o."TOTALBASKET") AS total_ventas,
            COUNT(DISTINCT b."BRANCH_ID") AS num_tiendas,
            COUNT(DISTINCT o."USERID") AS num_clientes,
            SUM(o."TOTALBASKET") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS ventas_por_tienda,
            COUNT(DISTINCT o."USERID") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS clientes_por_tienda
        FROM "Orders" o
        JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
        GROUP BY b."CITY"
        ORDER BY ventas_por_tienda DESC;
        """
    else:
        query_gasto = """
        SELECT 
            COALESCE(b."TOWN", c."TOWN") AS nivel,
            SUM(o."TOTALBASKET") AS total_ventas,
            COUNT(DISTINCT b."BRANCH_ID") AS num_tiendas,
            COUNT(DISTINCT o."USERID") AS num_clientes,
            SUM(o."TOTALBASKET") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS ventas_por_tienda,
            COUNT(DISTINCT o."USERID") / NULLIF(COUNT(DISTINCT b."BRANCH_ID"), 0) AS clientes_por_tienda
        FROM "Orders" o
        LEFT JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
        JOIN "Customers" c ON o."USERID" = c."USERID"
        GROUP BY COALESCE(b."TOWN", c."TOWN")
        ORDER BY ventas_por_tienda DESC;
        """

    # --- Pueblos sin tiendas (pesada → cacheada)
    query_pueblos_sin_tiendas = """
    SELECT 
        c."REGION",
        c."CITY",
        c."TOWN",
        COUNT(DISTINCT c."USERID") AS num_clientes
    FROM "Customers" c
    WHERE c."TOWN" NOT IN (SELECT DISTINCT "TOWN" FROM "Branches" WHERE "TOWN" IS NOT NULL)
    GROUP BY c."REGION", c."CITY", c."TOWN"
    ORDER BY num_clientes DESC
    LIMIT 15;
    """

    # ------------------------------------------------------
    # EJECUCIÓN CON CACHE
    # ------------------------------------------------------
    try:
        df_gasto = run_cached_query(query_gasto)
        df_pueblos = run_cached_query(query_pueblos_sin_tiendas)
    except Exception as e:
        st.error(f"Error al ejecutar las consultas: {e}")
        st.stop()

    # ------------------------------------------------------
    # VISUALIZACIONES
    # ------------------------------------------------------
    st.subheader(f"Rendimiento por {nivel}")

    if not df_gasto.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.bar(
                df_gasto.head(10),
                x="nivel",
                y="ventas_por_tienda",
                title=f"Top 10 {nivel.lower()}s con mayor gasto por tienda",
                text_auto=".2s",
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(
                df_gasto.head(10),
                x="nivel",
                y="clientes_por_tienda",
                title=f"Top 10 {nivel.lower()}s con más clientes por tienda",
                text_auto=".2s",
                color="clientes_por_tienda",
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No se encontraron datos para el nivel seleccionado.")

    st.divider()
    st.subheader("Pueblos con compradores pero sin tiendas")

    if not df_pueblos.empty:
        st.dataframe(df_pueblos, use_container_width=True)
    else:
        st.info("No hay pueblos sin tiendas registrados.")


# ==========================================================
# TAB 2 - RECOMENDADOR HEURÍSTICO
# ==========================================================
with tab2:
    st.subheader("Recomendador de nuevas ubicaciones")

    # --- Región (consulta ligera → sin cache)
    regiones = run_query('SELECT DISTINCT "REGION" FROM "Branches" ORDER BY "REGION";')["REGION"].tolist()
    region_sel = st.selectbox("Selecciona una región", regiones)

    # --- Consulta pesada → cacheada
    query_ciudades = f"""
    SELECT 
        c."CITY",
        COUNT(DISTINCT c."USERID") AS num_clientes,
        COUNT(DISTINCT b."BRANCH_ID") AS num_tiendas,
        SUM(o."TOTALBASKET") AS total_ventas
    FROM "Customers" c
    LEFT JOIN "Orders" o ON c."USERID" = o."USERID"
    LEFT JOIN "Branches" b ON c."CITY" = b."CITY"
    WHERE c."REGION" = '{region_sel}'
    GROUP BY c."CITY";
    """

    df = run_cached_query(query_ciudades)

    if df.empty:
        st.warning("No hay datos suficientes para esta región.")
        st.stop()

    # ------------------------------------------------------
    # HEURÍSTICA
    # ------------------------------------------------------
    df["clientes_por_tienda"] = df["num_clientes"] / df["num_tiendas"].replace(0, np.nan)
    df["ventas_por_tienda"] = df["total_ventas"] / df["num_tiendas"].replace(0, np.nan)

    # Normalización
    for col in ["clientes_por_tienda", "ventas_por_tienda"]:
        df[col + "_norm"] = 100 * (df[col] - df[col].min()) / (df[col].max() - df[col].min())

    df["score"] = 0.6 * df["clientes_por_tienda_norm"] + 0.4 * df["ventas_por_tienda_norm"]

    # Tamaño recomendado
    def recomendar_tamano(row):
        if row["clientes_por_tienda"] < 200:
            return "Pequeña"
        elif row["clientes_por_tienda"] < 1000:
            return "Mediana"
        else:
            return "Grande"

    df["tamano_recomendado"] = df.apply(recomendar_tamano, axis=1)

    # Categorías recomendadas
    def recomendar_categorias(tamano):
        if tamano == "Pequeña":
            return ["Electrónica"]
        elif tamano == "Mediana":
            return ["Electrónica", "Ropa", "Hogar", "Juguetes", "Deportes"]
        else:
            return ["Todas"]

    df["categorias_recomendadas"] = df["tamano_recomendado"].apply(recomendar_categorias)

    # Top 5
    top5 = df.sort_values("score", ascending=False).head(5)

    st.success(f"Top 5 ciudades recomendadas para abrir nuevas tiendas en {region_sel}:")
    st.dataframe(
        top5[["CITY", "num_clientes", "num_tiendas", "score", "tamano_recomendado", "categorias_recomendadas"]],
        use_container_width=True
    )

    fig = px.bar(
        top5,
        x="CITY",
        y="score",
        color="tamano_recomendado",
        text_auto=".2s",
        title="Ranking de ciudades recomendadas",
        labels={"CITY": "Ciudad", "score": "Puntuación de oportunidad"}
    )
    st.plotly_chart(fig, use_container_width=True)
