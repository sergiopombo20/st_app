import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query
import os

# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(page_title="Panel de Dirección", layout="wide")

# Mostrar logo arriba
logo_path = os.path.join("logo", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=120)

st.title("Panel de Dirección - Ventas y Análisis Global")

# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================
def plot_line(df, x, y, title):
    if df.empty:
        st.info("No hay datos disponibles.")
        return
    fig = px.line(df, x=x, y=y, markers=True, title=title,
                  labels={x: "Periodo", y: "Valor"})
    st.plotly_chart(fig, use_container_width=True)

def plot_bar(df, x, y, title, color=None):
    if df.empty:
        st.info("No hay datos disponibles.")
        return
    fig = px.bar(df, x=x, y=y, color=color, text_auto=".2s", title=title,
                 labels={x: x.title(), y: y.title()})
    st.plotly_chart(fig, use_container_width=True)

def plot_treemap(df, title="Distribución geográfica de ventas"):
    if df.empty:
        st.info("No hay información geográfica disponible.")
        return
    fig = px.treemap(df, path=["REGION", "CITY"], values="total_ventas",
                     color="total_ventas", color_continuous_scale="Viridis",
                     title=title)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# TABS PRINCIPALES
# ==========================================================
tab1, tab2 = st.tabs(["Análisis por Año", "Comparativa entre Años"])

# ==========================================================
# TAB 1 - ANÁLISIS POR AÑO
# ==========================================================
with tab1:
    st.subheader("Análisis por Año")

    # Filtros dentro del tab
    col1, col2 = st.columns([1, 2])
    with col1:
        year = st.selectbox("Año", [2021, 2022, 2023], index=1)
    with col2:
        region = st.text_input("Filtrar por región (opcional):")

    st.markdown("---")

    # ---------------- CONSULTAS ----------------
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

    query_evolucion = f"""
    SELECT 
        mes,
        SUM(total_ventas) AS total_ventas,
        SUM(num_pedidos) AS num_pedidos,
        AVG(ticket_medio) AS ticket_medio
    FROM mv_evolucion_mensual
    WHERE anio = {year}
    {"AND \"REGION\" ILIKE '%" + region + "%'" if region else ""}
    GROUP BY mes
    ORDER BY mes;
    """

    query_mapa = f"""
    SELECT 
        "REGION",
        "CITY",
        SUM(total_ventas) AS total_ventas,
        SUM(num_pedidos) AS num_pedidos,
        AVG(ticket_medio) AS ticket_medio
    FROM mv_ventas_mapa
    WHERE anio = {year}
    GROUP BY "REGION", "CITY"
    ORDER BY total_ventas DESC;
    """

    query_top_productos = f"""
    SELECT 
        "ITEMNAME",
        categoria,
        marca,
        ingresos,
        unidades
    FROM mv_top_productos
    WHERE anio = {year}
    ORDER BY ingresos DESC
    LIMIT 15;
    """

    query_top_categorias = f"""
    SELECT 
        categoria,
        ingresos,
        unidades
    FROM mv_top_categorias
    WHERE anio = {year}
    ORDER BY ingresos DESC
    LIMIT 10;
    """

    # ---------------- CARGA DE DATOS ----------------
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

    st.divider()
    st.subheader("Evolución de Ventas Mensuales")
    plot_line(evolucion, "mes", "total_ventas", f"Evolución mensual ({year})")

    st.divider()
    st.subheader("Ventas por Tienda / Región")
    plot_treemap(mapa)

    st.divider()
    st.subheader("Top 15 Productos por Ingresos")
    plot_bar(top_prod, "ITEMNAME", "ingresos", "Top Productos por Ingresos", "categoria")

    st.divider()
    st.subheader("Top 10 Categorías por Ingresos")
    plot_bar(top_cat, "categoria", "ingresos", "Top Categorías por Ingresos")

# ==========================================================
# TAB 2 - COMPARATIVA ENTRE AÑOS
# ==========================================================
with tab2:
    st.subheader("Comparativa entre Años")

    # Cargar lista de regiones desde la BD
    regiones_query = """
    SELECT DISTINCT b."REGION"
    FROM "Branches" b
    ORDER BY b."REGION";
    """
    regiones_df = run_query(regiones_query)
    regiones = regiones_df["REGION"].dropna().unique().tolist()

    st.markdown("#### Filtro de Regiones")
    regiones_seleccionadas = st.multiselect(
        "Selecciona una o varias regiones (si no seleccionas ninguna se mostrará el total global):",
        opciones := regiones,
        default=[]
    )

    # Si no hay regiones seleccionadas → consulta global
    if not regiones_seleccionadas:
        query_comparativa = """
        SELECT 
            EXTRACT(YEAR FROM o."DATE_") AS anio,
            SUM(o."TOTALBASKET") AS total_ventas,
            COUNT(o."ORDERID") AS num_pedidos,
            AVG(o."TOTALBASKET") AS ticket_medio
        FROM "Orders" o
        GROUP BY anio
        ORDER BY anio;
        """
        df_comp = run_query(query_comparativa)

        if not df_comp.empty:
            st.subheader("Ventas Totales (Todas las Regiones)")
            fig = px.bar(
                df_comp,
                x="anio",
                y="total_ventas",
                text_auto=".2s",
                title="Evolución Global de Ventas por Año",
                labels={"anio": "Año", "total_ventas": "Ventas (€)"}
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Evolución del Ticket Medio (Global)")
            fig2 = px.line(
                df_comp,
                x="anio",
                y="ticket_medio",
                markers=True,
                title="Evolución del Ticket Medio Global",
                labels={"anio": "Año", "ticket_medio": "Ticket Medio (€)"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No se encontraron datos para los años disponibles.")
    else:
        # Si hay regiones seleccionadas → consulta por región
        query_comparativa = f"""
        SELECT 
            EXTRACT(YEAR FROM o."DATE_") AS anio,
            b."REGION",
            SUM(o."TOTALBASKET") AS total_ventas,
            COUNT(o."ORDERID") AS num_pedidos,
            AVG(o."TOTALBASKET") AS ticket_medio
        FROM "Orders" o
        JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
        WHERE b."REGION" IN ({', '.join([f"'{r}'" for r in regiones_seleccionadas])})
        GROUP BY anio, b."REGION"
        ORDER BY anio, b."REGION";
        """
        df_comp = run_query(query_comparativa)

        if not df_comp.empty:
            st.subheader("Ventas por Región y Año")
            fig = px.bar(
                df_comp,
                x="anio",
                y="total_ventas",
                color="REGION",
                barmode="group",
                title="Comparativa de Ventas por Región y Año",
                labels={"anio": "Año", "total_ventas": "Ventas (€)", "REGION": "Región"}
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Ticket Medio por Región y Año")
            fig2 = px.line(
                df_comp,
                x="anio",
                y="ticket_medio",
                color="REGION",
                markers=True,
                title="Evolución del Ticket Medio por Región y Año",
                labels={"anio": "Año", "ticket_medio": "Ticket Medio (€)"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No se encontraron datos para las regiones seleccionadas.")
