import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query
import os

# ==========================================================
#  CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(
    page_title="Panel de Dirección",
    layout="wide"
)

logo_path = os.path.join("logo", "logo.png")

st.image(logo_path, width=120)

st.title("Panel de Dirección - Análisis Global de Ventas")

# ==========================================================
# FILTROS LATERALES
# ==========================================================
st.sidebar.header("Filtros")

year = st.sidebar.selectbox("Año", [2021, 2022, 2023], index=1)
region = st.sidebar.text_input("Filtrar por región (opcional):")

# ==========================================================
# CONSULTAS SQL
# ==========================================================

# --- KPI generales ---
query_kpis = f"""
SELECT 
    SUM(o."TOTALBASKET") AS total_ventas,
    COUNT(o."ORDERID") AS num_pedidos,
    AVG(o."TOTALBASKET") AS ticket_medio
FROM "Orders" o
JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
WHERE EXTRACT(YEAR FROM o."DATE_") = {year}
{"AND b.\"REGION\" ILIKE '%" + region + "%'" if region else ""};
"""

# --- Evolución mensual ---
query_evolucion = f"""
SELECT 
    DATE_TRUNC('month', o."DATE_"::timestamp) AS mes,
    SUM(o."TOTALBASKET") AS total_ventas,
    COUNT(o."ORDERID") AS num_pedidos,
    AVG(o."TOTALBASKET") AS ticket_medio
FROM "Orders" o
JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
WHERE EXTRACT(YEAR FROM o."DATE_") = {year}
{"AND b.\"REGION\" ILIKE '%" + region + "%'" if region else ""}
GROUP BY mes
ORDER BY mes;
"""

# --- Ventas por tienda / región ---
query_mapa = f"""
SELECT 
    b."REGION",
    b."CITY",
    SUM(o."TOTALBASKET") AS total_ventas
FROM "Orders" o
JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
WHERE EXTRACT(YEAR FROM o."DATE_") = {year}
GROUP BY b."REGION", b."CITY";
"""

# --- Top productos ---
query_top_productos = f"""
SELECT 
    c."ITEMNAME",
    c."CATEGORY1" AS categoria,
    c."BRAND" AS marca,
    SUM(od."TOTALPRICE") AS ingresos,
    SUM(od."AMOUNT") AS unidades
FROM "Order_Details" od
JOIN "Orders" o ON od."ORDERID" = o."ORDERID"
JOIN "Categories" c ON od."ITEMID" = c."ITEMID"
WHERE EXTRACT(YEAR FROM o."DATE_") = {year}
GROUP BY c."ITEMNAME", c."CATEGORY1", c."BRAND"
ORDER BY ingresos DESC
LIMIT 15;
"""

# --- Top categorías ---
query_top_categorias = f"""
SELECT 
    c."CATEGORY1" AS categoria,
    SUM(od."TOTALPRICE") AS ingresos,
    SUM(od."AMOUNT") AS unidades
FROM "Order_Details" od
JOIN "Orders" o ON od."ORDERID" = o."ORDERID"
JOIN "Categories" c ON od."ITEMID" = c."ITEMID"
WHERE EXTRACT(YEAR FROM o."DATE_") = {year}
GROUP BY c."CATEGORY1"
ORDER BY ingresos DESC
LIMIT 10;
"""

# ==========================================================
# CARGA DE DATOS DESDE NEON
# ==========================================================
try:
    kpis = run_query(query_kpis)
    evolucion = run_query(query_evolucion)
    mapa = run_query(query_mapa)
    top_prod = run_query(query_top_productos)
    top_cat = run_query(query_top_categorias)
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

# ==========================================================
# SECCIÓN 1 - KPIs GENERALES
# ==========================================================
st.subheader(f"Resumen General {year}")

col1, col2, col3 = st.columns(3)
if not kpis.empty:
    col1.metric("Ventas Totales", f"{kpis['total_ventas'][0]:,.0f} €")
    col2.metric("Nº Pedidos", f"{int(kpis['num_pedidos'][0]):,}")
    col3.metric("Ticket Medio", f"{kpis['ticket_medio'][0]:,.2f} €")
else:
    st.warning("No se encontraron datos para los filtros seleccionados.")

# ==========================================================
# SECCIÓN 2 - EVOLUCIÓN TEMPORAL
# ==========================================================
st.subheader("Evolución de Ventas Mensuales")
if not evolucion.empty:
    fig = px.line(
        evolucion,
        x="mes",
        y="total_ventas",
        title=f"Evolución mensual de ventas ({year})",
        markers=True,
        labels={"mes": "Mes", "total_ventas": "Ventas (€)"}
    )
    st.plotly_chart(fig, width='stretch')
else:
    st.info("No hay datos disponibles para el periodo seleccionado.")

# ==========================================================
# SECCIÓN 3 - ANÁLISIS GEOGRÁFICO
# ==========================================================
st.subheader("Ventas por Tienda / Región")
if not mapa.empty:
    fig_map = px.treemap(
        mapa,
        path=["REGION", "CITY"],
        values="total_ventas",
        color="total_ventas",
        color_continuous_scale="Viridis",
        title="Distribución geográfica de ventas"
    )
    st.plotly_chart(fig_map, width='stretch')
else:
    st.info("No hay información geográfica disponible.")

# ==========================================================
# 🛒 SECCIÓN 4 - TOP PRODUCTOS
# ==========================================================
st.subheader("Top 15 Productos por Ingresos")
if not top_prod.empty:
    fig_bar = px.bar(
        top_prod,
        x="ITEMNAME",
        y="ingresos",
        color="categoria",
        text_auto=".2s",
        title="Top 15 Productos por Ingresos (coloreado por Categoría)",
        labels={"ITEMNAME": "Producto", "ingresos": "Ingresos (€)", "categoria": "Categoría"}
    )
    st.plotly_chart(fig_bar, width='stretch')
else:
    st.info("No se encontraron productos para el periodo seleccionado.")

# ==========================================================
# SECCIÓN 5 - TOP CATEGORÍAS
# ==========================================================
st.subheader("Top 10 Categorías por Ingresos")
if not top_cat.empty:
    fig_cat = px.bar(
        top_cat,
        x="categoria",
        y="ingresos",
        text_auto=".2s",
        title="Top Categorías por Ingresos",
        labels={"categoria": "Categoría", "ingresos": "Ingresos (€)"}
    )
    st.plotly_chart(fig_cat, width='stretch')
else:
    st.info("No se encontraron categorías para el periodo seleccionado.")
