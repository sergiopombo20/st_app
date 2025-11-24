import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import run_query
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings


warnings.filterwarnings("ignore")

# ============================================
# 0. CONTROL DE ACCESO
# ============================================
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.stop()

if st.session_state.get("role") not in ("rrhh", "admin"):
    st.error("No tiene permisos para acceder a esta página.")
    st.stop()

st.title("RRHH — Optimización de Personal por Tienda")

# ============================================
# FUNCIÓN GENERAL PARA NORMALIZAR EMPLEADOS
# ============================================
def normalizar_empleados(x):
    """Convierte empleados a entero y garantiza mínimo 2."""
    if pd.isna(x):
        return None
    return max(2, int(round(x)))

# ============================================
# 1. CARGA DE DATOS
# ============================================
@st.cache_data
def load_data():
    q = """
    SELECT "TOWN", date, daily_sales
    FROM vw_sales_rrhh
    ORDER BY date;
    """
    df = run_query(q)
    df["date"] = pd.to_datetime(df["date"])
    return df

df_all = load_data()

# ============================================
# 2. CLASIFICACIÓN DE TIENDAS POR CUARTILES
# ============================================
sales_by_town = (
    df_all.groupby("TOWN")["daily_sales"]
    .sum()
    .reset_index()
    .rename(columns={"daily_sales": "total_sales"})
    .sort_values("total_sales")
)

q1 = sales_by_town["total_sales"].quantile(0.25)
q2 = sales_by_town["total_sales"].quantile(0.50)
q3 = sales_by_town["total_sales"].quantile(0.75)

def clasificar(t):
    if t <= q1:
        return "Pequeña"
    elif t <= q2:
        return "Mediana"
    elif t <= q3:
        return "Grande"
    else:
        return "Muy grande"

sales_by_town["categoria"] = sales_by_town["total_sales"].apply(clasificar)

empleados_fijos = {
    "Pequeña": 5,
    "Mediana": 10,
    "Grande": 30,
    "Muy grande": 40
}

st.subheader("Clasificación de tiendas (por ventas totales)")
st.dataframe(sales_by_town)

# ============================================
# 3. SELECCIÓN DE TIENDA
# ============================================
tiendas = sales_by_town["TOWN"].tolist()
tienda_sel = st.selectbox("Selecciona tienda:", tiendas)

cat_tienda = sales_by_town.loc[sales_by_town["TOWN"] == tienda_sel, "categoria"].iloc[0]
empleados_constantes = normalizar_empleados(empleados_fijos[cat_tienda])

st.info(
    f"Tienda **{tienda_sel}** → Categoría **{cat_tienda}** → "
    f"Empleados actuales: **{empleados_constantes}**"
)

# ============================================
# 4. DATOS DIARIOS DE ESA TIENDA (HISTÓRICO COMPLETO)
# ============================================
df_store_daily = (
    df_all[df_all["TOWN"] == tienda_sel]
    .groupby("date", as_index=False)["daily_sales"]
    .sum()
    .sort_values("date")
)

if df_store_daily.empty:
    st.error("No hay datos para esta tienda.")
    st.stop()

# ============================================
# 5. FILTRAR SOLO ÚLTIMOS 30 DÍAS PARA MODELO Y GRÁFICA
# ============================================
fecha_max = df_store_daily["date"].max()
fecha_min_30 = fecha_max - pd.Timedelta(days=30)

df_30 = df_store_daily[df_store_daily["date"] >= fecha_min_30].copy()

if df_30.empty:
    st.error("No hay datos en los últimos 30 días para esta tienda.")
    st.stop()

df_30["empleados_ideales"] = (
    df_30["daily_sales"] / 5000
).apply(normalizar_empleados)

df_30["empleados_actuales"] = empleados_constantes

# ============================================
# 6. ENTRENAR SARIMA (ÚLTIMOS 30 DÍAS)
# ============================================
ts = df_30.set_index("date")["daily_sales"]

if len(ts) < 10:
    st.error("No hay suficientes datos en los últimos 30 días para entrenar SARIMA.")
    st.stop()

try:
    model = SARIMAX(
        ts,
        order=(2, 1, 2),
        seasonal_order=(1, 1, 1, 7),
        enforce_stationarity=True,       # forzamos más estabilidad
        enforce_invertibility=True,
    )
    res = model.fit(disp=False)
except Exception as e:
    st.error(f"Error entrenando SARIMA: {e}")
    st.stop()

# ============================================
# 7. PREDICCIÓN 7 DÍAS (LIMPIA)
# ============================================
steps = 7
pred_vals = res.forecast(steps)

future_dates = pd.date_range(
    start=ts.index.max(),
    periods=steps + 1,
    freq="D"
)[1:]

df_pred = pd.DataFrame({
    "date": future_dates,
    "daily_sales": pred_vals.values
})

# ---- LIMPIAR PREDICCIONES RARAS ----
max_hist = df_30["daily_sales"].max()

# - No permitir ventas negativas
# - No permitir predicciones > 3x el máximo histórico reciente
df_pred["daily_sales"] = df_pred["daily_sales"].clip(lower=0, upper=max_hist * 3)

df_pred["empleados_pred"] = (
    df_pred["daily_sales"] / 5000
).apply(normalizar_empleados)

# ============================================
# 8. UNIR DATOS PARA GRÁFICA
# ============================================
df_plot = pd.concat([
    df_30[["date", "empleados_actuales", "empleados_ideales"]],
    df_pred[["date", "empleados_pred"]]
])

df_melt = df_plot.melt(
    id_vars="date",
    var_name="tipo",
    value_name="empleados"
)

legend_map = {
    "empleados_actuales": "Empleados actuales",
    "empleados_ideales": "Empleados ideales (ventas/10k)",
    "empleados_pred": "Empleados predichos (SARIMA)"
}
df_melt["label"] = df_melt["tipo"].map(legend_map)

# ============================================
# 9. GRÁFICA ÚNICA
# ============================================
fig = px.line(
    df_melt,
    x="date",
    y="empleados",
    color="label",
    markers=True,
    title=f"Planificación de Personal — {tienda_sel}",
    template="plotly_white"
)

fig.update_layout(
    hovermode="x unified",
    xaxis_title="Fecha",
    yaxis_title="Número de empleados"
)

st.plotly_chart(fig, use_container_width=True)

# ============================================
# 10. SELECTOR DE FECHA (HISTÓRICOS + PREDICCIONES)
# ============================================
fechas_hist = df_30["date"].dt.date.unique().tolist()
fechas_pred = df_pred["date"].dt.date.unique().tolist()
fechas_disponibles = sorted(fechas_hist + fechas_pred)

fecha_sel = st.date_input(
    "Selecciona fecha para ver detalles:",
    value=fechas_disponibles[-1],
    min_value=min(fechas_disponibles),
    max_value=max(fechas_disponibles)
)

fecha_sel = pd.to_datetime(fecha_sel)

# ============================================
# 11. VENTAS DEL DÍA SELECCIONADO (REAL O PREDICCIÓN LIMPIA)
# ============================================
ventas_dia = None
es_prediccion = False

fila_hist = df_store_daily[df_store_daily["date"] == fecha_sel]
if not fila_hist.empty:
    ventas_dia = fila_hist["daily_sales"].iloc[0]
else:
    fila_pred = df_pred[df_pred["date"] == fecha_sel]
    if not fila_pred.empty:
        ventas_dia = fila_pred["daily_sales"].iloc[0]
        es_prediccion = True

if ventas_dia is None:
    st.warning("No hay datos de ventas para la fecha seleccionada.")
    st.stop()

# Por seguridad extra, nunca permitimos ventas negativas aquí
if ventas_dia < 0:
    ventas_dia_original = ventas_dia
    ventas_dia = 0
    st.warning(
        f"La predicción original para ese día era negativa ({ventas_dia_original:,.2f} €). "
        f"Se ha ajustado a 0 € porque no tiene sentido facturación negativa."
    )

# ============================================
# 12. BENEFICIOS (ACTUALES VS MODELO)
# ============================================
empleados_modelo = normalizar_empleados(ventas_dia / 5000)

beneficio_const = 0.08 * ventas_dia - 200 * empleados_constantes
beneficio_modelo = 0.08 * ventas_dia - 200 * empleados_modelo

st.subheader(f"Resultados para {fecha_sel.date()}")

st.write(f"**Ventas del día:** {ventas_dia:,.2f} €")
st.write(f"**Empleados actuales:** {empleados_constantes}")
st.write(f"**Beneficio (empleados actuales):** {beneficio_const:,.2f} €")
st.write(f"**Empleados modelo:** {empleados_modelo}")
st.write(f"**Beneficio (modelo):** {beneficio_modelo:,.2f} €")


# ============================================
# 13. ÚLTIMOS 5 DÍAS (MISMO DÍA DE LA SEMANA)
# ============================================
weekday_sel = fecha_sel.weekday()

df_week = df_store_daily.copy()
df_week["weekday"] = df_week["date"].dt.weekday

historico = df_week[
    (df_week["weekday"] == weekday_sel) &
    (df_week["date"] < fecha_sel)
].tail(5)

st.subheader("📚 Últimos 5 días del mismo día de la semana")

if historico.empty:
    st.warning("No hay históricos suficientes.")
else:

    # Empleados modelo (ventas / 10k)
    historico["empleados_modelo"] = (
        historico["daily_sales"] / 10000
    ).apply(normalizar_empleados)

    # Empleados fijos del método antiguo
    historico["empleados_antiguos"] = empleados_constantes

    # Beneficios
    historico["beneficio_modelo"] = (
        0.12 * historico["daily_sales"] -
        120 * historico["empleados_modelo"]
    )

    historico["beneficio_antiguo"] = (
        0.12 * historico["daily_sales"] -
        120 * historico["empleados_antiguos"]
    )

    # Comparación: verde si el modelo es mejor, rojo si peor
    historico["mejora_html"] = historico.apply(
        lambda row: (
            f"<span style='color:green;font-weight:bold;'>✔ {row['beneficio_modelo'] - row['beneficio_antiguo']:+.2f} €</span>"
            if row["beneficio_modelo"] > row["beneficio_antiguo"]
            else f"<span style='color:red;font-weight:bold;'>✘ {row['beneficio_modelo'] - row['beneficio_antiguo']:+.2f} €</span>"
        ),
        axis=1
    )

    # Mostrar tabla bonita
    st.markdown("""
    ### Comparación modelo vs método antiguo
    <small>(verde = mejora, rojo = peor)</small>
    """, unsafe_allow_html=True)

    tabla = historico[[
        "date",
        "daily_sales",
        "empleados_antiguos",
        "empleados_modelo",
        "beneficio_antiguo",
        "beneficio_modelo",
        "mejora_html"
    ]].copy()

    tabla.columns = [
        "Fecha",
        "Ventas (€)",
        "Emp. antiguos",
        "Emp. modelo",
        "Beneficio antiguo (€)",
        "Beneficio modelo (€)",
        "Diferencia"
    ]

    # Render HTML in Streamlit table
    st.write(tabla.to_html(escape=False, index=False), unsafe_allow_html=True)

