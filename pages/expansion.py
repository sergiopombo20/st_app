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
# TABS
# ==========================================================
tab1, tab2 = st.tabs(["Análisis de Oportunidades", "Simulador Predictivo"])

# ==========================================================
# TAB 1: ANÁLISIS DE OPORTUNIDADES (TAL CUAL LO TENÍAS)
# ==========================================================
with tab1:
    st.subheader("Filtros de análisis")

    nivel = st.selectbox("Nivel de análisis", ["Región", "Ciudad", "Pueblo (Town)"], index=0)
    st.divider()

    # --- CONSULTAS SQL ---
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

    try:
        df_gasto = run_query(query_gasto)
        df_pueblos = run_query(query_pueblos_sin_tiendas)
    except Exception as e:
        st.error(f"Error al ejecutar las consultas: {e}")
        st.stop()

    # --- Visualizaciones ---
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


# ==========================================================
# TAB 2: SIMULADOR PREDICTIVO (HEURÍSTICO)
# ==========================================================
with tab2:
    st.subheader("Recomendador de Nuevas Ubicaciones por Región (Nivel: Ciudad)")

    regiones = run_query('SELECT DISTINCT "REGION" FROM "Customers" ORDER BY "REGION";')
    region_sel = st.selectbox("Selecciona una región", regiones["REGION"].dropna().tolist())

    query = f"""
    SELECT 
        c."REGION",
        c."CITY",
        COUNT(DISTINCT c."USERID") AS num_clientes,
        COALESCE(SUM(o."TOTALBASKET"), 0) AS total_ventas,
        COUNT(DISTINCT b."BRANCH_ID") AS num_tiendas
    FROM "Customers" c
    LEFT JOIN "Orders" o ON c."USERID" = o."USERID"
    LEFT JOIN "Branches" b ON c."CITY" = b."CITY"
    WHERE c."REGION" = '{region_sel}'
    GROUP BY c."REGION", c."CITY";
    """

    try:
        df = run_query(query)
    except Exception as e:
        st.error(f"Error al cargar datos de la región: {e}")
        st.stop()

    if df.empty:
        st.warning("No hay datos suficientes para esta región.")
        st.stop()

    # Calcular métricas básicas
    df["ticket_medio"] = df["total_ventas"] / df["num_clientes"].replace(0, 1)
    df["beneficio_base"] = df["num_clientes"] * df["ticket_medio"]

    # Penalización por nº de tiendas
    def penalizacion_tiendas(n):
        if n == 0:
            return 0.4
        elif n <= 2:
            return 0.7
        else:
            return 1.0

    df["penalizacion_tiendas"] = df["num_tiendas"].apply(penalizacion_tiendas)

    # Tamaño recomendado según la cantidad de clientes
    df["tamano_recomendado"] = pd.cut(
        df["num_clientes"],
        bins=[-1, 2000, 6000, float("inf")],
        labels=["Pequeña", "Mediana", "Grande"]
    )

    df["factor_tamano"] = df["tamano_recomendado"].map({
        "Pequeña": 1.0,
        "Mediana": 2.0,
        "Grande": 3.0
    })

    # Beneficio esperado y score final (normalizado)
    df["beneficio_esperado"] = (
        df["beneficio_base"] * df["factor_tamano"] * df["penalizacion_tiendas"]
    )
    df["score_final"] = df["beneficio_esperado"] / (df["num_clientes"].replace(0, 1) ** 0.5)

    # Filtrar ciudades con baja demanda
    df = df[df["num_clientes"] >= 500]

    # Ordenar y seleccionar top
    df_top = df.sort_values(by="score_final", ascending=False).head(5)

    # Categorías sugeridas
    categorias = run_query('SELECT DISTINCT "CATEGORY1" FROM "Categories";')["CATEGORY1"].dropna().tolist()
    top_categorias = categorias[:5]

    st.subheader(f"Top 5 ciudades recomendadas en {region_sel}")
    st.dataframe(df_top[["CITY", "num_clientes", "num_tiendas", "tamano_recomendado", "score_final"]], use_container_width=True)

    for _, row in df_top.iterrows():
        st.markdown(f"### {row['CITY']}")
        st.write(f"- Clientes: {int(row['num_clientes'])}")
        st.write(f"- Tiendas actuales: {int(row['num_tiendas'])}")
        st.write(f"- Tamaño recomendado: **{row['tamano_recomendado']}**")

        # Categorías sugeridas según tamaño
        if row["tamano_recomendado"] == "Pequeña":
            cats = [categorias[0]]
        elif row["tamano_recomendado"] == "Mediana":
            cats = top_categorias
        else:
            cats = categorias

        st.write("Categorías recomendadas:", ", ".join(cats))
        st.write(f"Score de rentabilidad estimado: {row['score_final']:.2f}")
        st.divider()
