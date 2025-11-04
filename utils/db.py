import pandas as pd
from sqlalchemy import create_engine

# 🔗 Conexión a Neon
DB_URL = 'postgresql://neondb_owner:npg_ewIv6k9gCGlK@ep-little-shadow-ab3l0o9a-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

engine = create_engine(DB_URL)

def run_query(query: str) -> pd.DataFrame:
    """Ejecuta una consulta SQL en Neon y devuelve los resultados como DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(query, conn)
