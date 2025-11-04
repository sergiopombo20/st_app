import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query

st.set_page_config(page_title="Dirección - Dashboard", layout="wide")

st.title("📈 Panel de Dirección")
st.markdown("### Resumen general de ventas y rendimiento")

# --- 1️⃣ Consultas a Neon ---
orders = run_query("""
    SELECT o."ORDERID", o."BRANCH_ID", o."TOTALBASKET", o."DATE_", 
           b."CITY", b."REGION"
    FROM "Orders" o
    JOIN "Branches" b ON o."BRANCH_ID" = b."BRANCH_ID";
""")

details = run_query("""
    SELECT d."ORDERID", d."ITEMID", d."AMOUNT", d."TOTALPRICE", c."ITEMCODE"
    FROM "Order_Details" d
    JOIN "Categories" c ON d."ITEMID" = c."ITEMID";
""")

# --- 2️⃣ KPIs ---
total_ventas = orders["TOTALBASKET"].astype(float).sum()
num_pedidos = len(orders)
ticket_medio = total_ventas / num_pedidos if num_pedidos > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ventas totales", f"{total_ventas:,.0f} €")
col2.metric("🧾 Número de pedidos", f"{num_pedidos:,}")
col3.metric("💳 Ticket medio", f"{ticket_medio:,.2f} €")

st.divider()

# --- 3️⃣ Ventas por región ---
ventas_region = (
    orders.groupby("REGION")["TOTALBASKET"]
    .sum()
    .reset_index()
    .sort_values("TOTALBASKET", ascending=False)
)
fig_region = px.bar(
    ventas_region,
    x="REGION", y="TOTALBASKET",
    title="Ventas totales por región",
    text_auto=True
)
st.plotly_chart(fig_region, use_container_width=True)

# --- 4️⃣ Productos más vendidos ---
productos_top = (
    details.groupby("ITEMCODE")["AMOUNT"]
    .sum()
    .reset_index()
    .sort_values("AMOUNT", ascending=False)
    .head(10)
)
fig_top = px.bar(
    productos_top,
    x="ITEMCODE", y="AMOUNT",
    title="Top 10 productos más vendidos",
    text_auto=True
)
st.plotly_chart(fig_top, use_container_width=True)

# --- 5️⃣ Mapa interactivo de ventas ---
branches = run_query('SELECT "BRANCH_ID", "CITY", "REGION" FROM "Branches";')
ventas_mapa = (
    orders.groupby(["BRANCH_ID", "CITY", "REGION"])["TOTALBASKET"]
    .sum()
    .reset_index()
    .merge(branches, on="BRANCH_ID", how="left")
)

st.map(ventas_mapa.rename(columns={"LAT": "lat", "LON": "lon"}))
