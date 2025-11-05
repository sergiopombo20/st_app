import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query
import os

# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(page_title="Panel de Expansión", layout="wide")

logo_path = os.path.join("logo", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=120)

st.title("Panel de Expansión - Oportunidades de Crecimiento")

# ==========================================================
# FILTROS
# ==========================================================
st.subheader("Filtros de análisis")

nivel = st.selectbox("Nivel de análisis", ["Región", "Ciudad", "Pueblo (Town)"], index=0)


st.divider()

# ==========================================================
# CONSULTAS SQL
# ==========================================================

# --- 1️⃣ Gasto total y tiendas ---
if nivel == "Región":
    query_gasto = f"""
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
    query_gasto = f"""
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

else:  # Pueblo (TOWN)
    query_gasto = f"""
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

# --- 2️⃣ Pueblos con compradores y sin tiendas ---
query_pueblos_sin_tiendas = f"""
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

# ==========================================================
# CARGA DE DATOS
# ==========================================================
try:
    df_gasto = run_query(query_gasto)
    df_pueblos = run_query(query_pueblos_sin_tiendas)
except Exception as e:
    st.error(f"Error al ejecutar las consultas: {e}")
    st.stop()

# ==========================================================
# VISUALIZACIONES
# ==========================================================
st.subheader(f"Rendimiento por {nivel}")

if not df_gasto.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(
            df_gasto.head(10),
            x="nivel",
            y="ventas_por_tienda",
            title=f"Regiones con mayor gasto por tienda" if nivel=="Región" else f"Top 10 {nivel.lower()}s con mayor gasto por tienda",
            labels={"nivel": nivel, "ventas_por_tienda": "Ventas por tienda (€)"},
            text_auto=".2s",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.bar(
            df_gasto.head(15),
            x="nivel",
            y="clientes_por_tienda",
            title=f"Regiones con más clientes por tienda" if nivel=="Región" else f"Top 10 {nivel.lower()}s con más clientes por tienda",
            labels={"nivel": nivel, "clientes_por_tienda": "Clientes por tienda"},
            text_auto=".2s",
            color="clientes_por_tienda",
        )
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No se encontraron datos para el periodo seleccionado.")

st.divider()
st.subheader("Pueblos con Compradores pero sin Tiendas")

if not df_pueblos.empty:
    st.dataframe(df_pueblos, use_container_width=True)
    fig3 = px.bar(
        df_pueblos.head(15),
        x="TOWN",
        y="num_clientes",
        color="CITY",
        title="Top 15 pueblos con más clientes y sin tiendas",
        labels={"TOWN": "Pueblo", "num_clientes": "Clientes"}
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No hay pueblos sin tiendas registrados.")
