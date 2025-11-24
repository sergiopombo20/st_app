import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.db import run_query
import os


# ==========================================================
# CONTROL DE ACCESO
# ==========================================================

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.stop()

if st.session_state.get("role") not in ("admin", "direccion"):
    st.error("No tiene permisos para acceder a este panel.")
    st.stop()



# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(page_title="Panel de Dirección", layout="wide")

logo_path = os.path.join("logo", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=120)

st.title("Panel de Dirección - Ventas y Análisis Global")


# ==========================================================
# FUNCIONES AUXILIARES DE VISUALIZACIÓN
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
    fig = px.treemap(
        df,
        path=["REGION", "CITY"],
        values="total_ventas",
        color="total_ventas",
        color_continuous_scale="Viridis",
        title=title
    )
    st.plotly_chart(fig, use_container_width=True)


# ==========================================================
# TABS PRINCIPALES
# ==========================================================
tab1, tab2, tab3 = st.tabs(["Análisis por Año", "Comparativa entre Años", "Predicción de Ventas"])


# ==========================================================
# TAB 1 — ANÁLISIS POR AÑO
# ==========================================================
with tab1:
    st.subheader("Análisis por Año")

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
    # SECCIÓN — KPIs
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
# TAB 2 — COMPARATIVA ENTRE AÑOS
# ==========================================================
with tab2:
    st.subheader("Comparativa entre Años")

    regiones_query = """
    SELECT DISTINCT b."REGION"
    FROM "Branches" b
    ORDER BY b."REGION";
    """

    regiones_df = run_query(regiones_query)
    regiones = regiones_df["REGION"].dropna().unique().tolist()

    st.markdown("#### Filtro de Regiones")

    regiones_seleccionadas = st.multiselect(
        "Selecciona una o varias regiones:",
        regiones,
        default=[]
    )

    # Consulta global si no se selecciona nada
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
            st.subheader("Ventas Totales (Global)")
            fig = px.bar(
                df_comp,
                x="anio",
                y="total_ventas",
                title="Evolución Global de Ventas",
                text_auto=".2s"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Ticket Medio Global")
            fig2 = px.line(
                df_comp,
                x="anio",
                y="ticket_medio",
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay datos disponibles.")
    else:
        # Consulta por regiones seleccionadas
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
                text_auto=".2s"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Ticket Medio por Región")
            fig2 = px.line(
                df_comp,
                x="anio",
                y="ticket_medio",
                color="REGION",
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No se encontraron datos para esas regiones.")

# ==========================================================
# TAB 3 — PREDICCIÓN DE VENTAS (OPTIMIZADO + CORREGIDO)
# ==========================================================

import numpy as np
import pandas as pd
import plotly.express as px
from tensorflow.keras.models import load_model
import pickle

# ============================================
# 0. CACHE DE DATOS (solo se consulta una vez)
# ============================================
@st.cache_data
def load_all_sales():
    query = """
    SELECT 
        o."DATE_" AS date,
        o."TOTALBASKET" AS daily_sales,
        b."REGION",
        b."CITY"
    FROM "Orders" o
    LEFT JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID"
    ORDER BY o."DATE_";
    """
    df = run_query(query)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ============================================
# 1. CACHE DE MODELOS (se carga solo una vez)
# ============================================
@st.cache_resource
def load_models():
    models = {}

    # SARIMA
    with open("modelos/sarima_final_model.pkl", "rb") as f:
        models["SARIMA"] = pickle.load(f)

    # Random Forest
    with open("modelos/random_forest_sales.pkl", "rb") as f:
        models["RF"] = pickle.load(f)

    # XGBoost
    with open("modelos/xgboost_sales_model.pkl", "rb") as f:
        models["XGB"] = pickle.load(f)

    # LSTM (corregido: compile=False)
    models["LSTM_MODEL"] = load_model("modelos/lstm_sales_model.h5", compile=False)

    with open("modelos/lstm_scaler.pkl", "rb") as f:
        models["LSTM_SCALER"] = pickle.load(f)
    # LSTM estilo PDF
    models["LSTM_PDF"] = load_model("modelos/lstm_pdf_model.h5", compile=False)
    with open("modelos/lstm_pdf_scaler.pkl", "rb") as f:
        models["LSTM_PDF_SCALER"] = pickle.load(f)


    return models


# ============================================
# 2. PREDICCIÓN UNIFICADA PARA TODOS LOS MODELOS
# ============================================
def predict(modelo_sel, ts, horizonte, _models):
    modelo_sel = modelo_sel.upper()

    # ===== SARIMA =====
    if modelo_sel == "SARIMA":
        return _models["SARIMA"].forecast(steps=horizonte).values

    # ===== RANDOM FOREST / XGBOOST =====
    if modelo_sel in ["RANDOM FOREST", "XGBOOST"]:
        model = _models["RF"] if modelo_sel == "RANDOM FOREST" else _models["XGB"]

        future_dates = pd.date_range(start=ts.index.max(), periods=horizonte+1, freq="D")[1:]
        df_future = pd.DataFrame({"date": future_dates})

        df_future["day"] = df_future.date.dt.day
        df_future["month"] = df_future.date.dt.month
        df_future["dow"] = df_future.date.dt.dayofweek

        df_future["day_sin"]   = np.sin(2*np.pi*df_future["day"] / 31)
        df_future["day_cos"]   = np.cos(2*np.pi*df_future["day"] / 31)
        df_future["month_sin"] = np.sin(2*np.pi*df_future["month"] / 12)
        df_future["month_cos"] = np.cos(2*np.pi*df_future["month"] / 12)
        df_future["dow_sin"]   = np.sin(2*np.pi*df_future["dow"] / 7)
        df_future["dow_cos"]   = np.cos(2*np.pi*df_future["dow"] / 7)

        X = df_future[["day_sin","day_cos","month_sin","month_cos","dow_sin","dow_cos"]]
        return model.predict(X)

    # ===== LSTM =====
    if modelo_sel == "LSTM":
        lstm = _models["LSTM_MODEL"]
        scaler = _models["LSTM_SCALER"]

        last_window = ts.values[-14:]
        seq = scaler.transform(last_window.reshape(-1,1))
        preds = []

        for _ in range(horizonte):
            p = lstm.predict(seq.reshape(1,14,1), verbose=0)
            preds.append(p[0][0])
            seq = np.vstack([seq[1:], p])

        return scaler.inverse_transform(np.array(preds).reshape(-1,1)).flatten()
    
    # ========= LSTM ESTILO PDF ==========
    if modelo_sel.upper() == "LSTM_PDF":
        lstm = _models["LSTM_PDF"]
        scaler = _models["LSTM_PDF_SCALER"]

        time_steps = 50

        # Última secuencia real
        last_seq = ts.values[-time_steps:].reshape(-1,1)

        # Normalizar igual que en entrenamiento
        last_scaled = scaler.transform(last_seq).reshape(-1)

        seq = last_scaled.copy()
        preds = []

        for _ in range(horizonte):
            x = seq[-time_steps:].reshape(1, time_steps, 1)
            p = lstm.predict(x, verbose=0)[0][0]
            preds.append(p)
            seq = np.append(seq, p)

        preds = scaler.inverse_transform(np.array(preds).reshape(-1,1)).flatten()
        return preds

# ============================================
# 3. CACHE DE PREDICCIÓN
# ============================================
@st.cache_data
def cached_prediction(modelo_sel, horizonte, region, ciudad, ts, _models):
    return predict(modelo_sel, ts, horizonte, _models)


# ============================================
# 4. UI DEL TAB
# ============================================
with tab3:
    st.subheader("Predicción de Ventas Futuras")

    # ===== Cargar datos y modelos caché =====
    df_all = load_all_sales()
    models = load_models()

    # ============================================
    # 4.1 Filtros región / ciudad / modelo
    # ============================================
    regiones = ["Todas"] + sorted(df_all["REGION"].dropna().unique().tolist())
    ciudades = ["Todas"]

    col1, col2, col3 = st.columns([1,1,1])

    with col1:
        region_sel = st.selectbox("Región:", regiones, index=0)

    if region_sel != "Todas":
        ciudades += sorted(df_all[df_all["REGION"] == region_sel]["CITY"].dropna().unique().tolist())

    with col2:
        ciudad_sel = st.selectbox("Ciudad:", ciudades, index=0)

    with col3:
        modelo_sel = st.selectbox("Modelo:", ["SARIMA", "Random Forest", "XGBoost", "LSTM", "LSTM_PDF"])

    horizonte = st.radio("Horizonte de predicción:", [30, 90], horizontal=True)

    # ============================================
    # 4.2 Filtrar datos sin tocar la base
    # ============================================
    df = df_all.copy()

    if region_sel != "Todas":
        df = df[df["REGION"] == region_sel]

    if ciudad_sel != "Todas":
        df = df[df["CITY"] == ciudad_sel]

    df = df.groupby("date")["daily_sales"].sum().reset_index()
    df = df.sort_values("date")
    ts = df.set_index("date")["daily_sales"]

    if ts.empty:
        st.warning("No hay datos disponibles para estos filtros.")
        st.stop()

    # ============================================
    # 4.3 Predicción cacheada (rápido)
    # ============================================
    pred = cached_prediction(modelo_sel, horizonte, region_sel, ciudad_sel, ts, models)

    # ============================================
    # 4.4 Mostrar SOLO datos recientes desde 2023
    # ============================================
    fecha_corte = pd.to_datetime("2023-01-01")
    ts_reciente = ts[ts.index >= fecha_corte]

    df_real = ts_reciente.reset_index().rename(columns={"daily_sales":"value"})
    df_real["tipo"] = "Real"

    future_dates = pd.date_range(start=ts.index.max(), periods=horizonte+1, freq="D")[1:]
    df_pred = pd.DataFrame({"date": future_dates, "value": pred, "tipo": "Predicción"})

    df_full = pd.concat([df_real, df_pred])

    # ============================================
    # 4.5 Gráfica REAL + PRED
    # ============================================
    fig = px.line(
        df_full,
        x="date",
        y="value",
        color="tipo",
        title=f"Predicción de Ventas — Modelo {modelo_sel}",
        template="plotly_white"
    )

    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Ventas",
        hovermode="x unified",
        legend_title="Serie",
    )

    st.plotly_chart(fig, use_container_width=True)
