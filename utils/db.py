import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from functools import lru_cache

# ==========================================================
# ⚙️ CONFIGURACIÓN DE CONEXIÓN A NEON
# ==========================================================
DB_URL = 'postgresql://neondb_owner:npg_ewIv6k9gCGlK@ep-little-shadow-ab3l0o9a-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

# ==========================================================
# 🔗 GESTIÓN EFICIENTE DE LA CONEXIÓN
# ==========================================================
@lru_cache
def get_engine():
    """Devuelve una instancia de SQLAlchemy Engine cacheada (reutilizable)."""
    return create_engine(DB_URL, pool_pre_ping=True)


# ==========================================================
# 🚀 FUNCIÓN PARA EJECUTAR CONSULTAS (CACHEADA)
# ==========================================================
@st.cache_data(show_spinner=False, ttl=600)
def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """
    Ejecuta una consulta SQL y devuelve un DataFrame.
    - Usa PyArrow para acelerar la carga.
    - Cachea los resultados durante 10 minutos.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(
                sql=text(query),
                con=conn,
                params=params,
                dtype_backend="pyarrow"  # Mucho más rápido que el backend estándar
            )
        return df

    except Exception as e:
        st.error(f"❌ Error al ejecutar la consulta:\n{e}")
        return pd.DataFrame()


# ==========================================================
# 🧩 FUNCIÓN AUXILIAR: EJECUTAR COMANDOS SQL (sin resultado)
# ==========================================================
def execute_query(query: str, params: dict | None = None) -> None:
    """
    Ejecuta una consulta SQL que no devuelve resultados (CREATE, DROP, REFRESH, etc.)
    """
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
    except Exception as e:
        st.error(f"⚠️ Error ejecutando comando SQL: {e}")
