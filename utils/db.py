import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==========================================================
# CARGA DE VARIABLES DE ENTORNO
# ==========================================================
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("Falta la variable DATABASE_URL en el archivo .env")


# ==========================================================
# ENGINE CACHEADO (solo se crea una vez)
# ==========================================================
@st.cache_resource
def get_engine():
    """Devuelve una conexión cacheada para evitar recrear el engine cada vez."""
    return create_engine(DB_URL, pool_pre_ping=True)


engine = get_engine()


# ==========================================================
# CONSULTA SIN CACHÉ
# ==========================================================
def run_query(query: str) -> pd.DataFrame:
    """
    Ejecuta una consulta SELECT sin usar caché.
    """
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


# ==========================================================
# CONSULTA CON CACHÉ (para queries pesadas)
# ==========================================================
@st.cache_data(show_spinner=False)
def run_cached_query(query: str) -> pd.DataFrame:
    """
    Ejecuta una consulta SELECT usando caché.
    Solo usar para consultas pesadas.
    """
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


# ==========================================================
# OPCIONAL: CONSULTAS DE ESCRITURA (por si las usas en el futuro)
# ==========================================================
def execute_query(query: str) -> None:
    """
    Ejecuta una consulta SQL que modifica datos (INSERT, UPDATE, DELETE, DDL).
    """
    with engine.connect() as conn:
        conn.execute(text(query))
        conn.commit()
