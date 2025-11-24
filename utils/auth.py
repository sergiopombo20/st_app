import bcrypt
from utils.db import run_query, execute_query
import re


# ==========================================================
# VALIDACIÓN DE DOMINIOS PERMITIDOS
# ==========================================================

VALID_DOMAINS = {
    "@admin3a.com": "admin",
    "@direccion3a.com": "direccion",
    "@expansion3a.com": "expansion",
}


def get_role_from_email(email: str):
    """
    Devuelve el rol según el dominio del email.
    """
    for domain, role in VALID_DOMAINS.items():
        if email.endswith(domain):
            return role
    return None



# ==========================================================
# HASHING DE CONTRASEÑA
# ==========================================================

def hash_password(password: str) -> str:
    """
    Genera un hash seguro con bcrypt.
    """
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifica si la contraseña coincide con el hash almacenado.
    """
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False



# ==========================================================
# GESTIÓN DE USUARIOS
# ==========================================================

def user_exists(email: str) -> bool:
    query = f"SELECT email FROM Users WHERE email = '{email}'"
    df = run_query(query)
    return not df.empty


def get_user(email: str):
    """
    Devuelve fila del usuario o None si no existe.
    """
    query = f"SELECT email, password_hash, role FROM Users WHERE email = '{email}'"
    df = run_query(query)
    if df.empty:
        return None
    return df.iloc[0].to_dict()



def create_user(email: str, password: str, role: str = None) -> bool:
    """
    Crea un usuario nuevo con hash seguro.
    - Si no se indica role, se obtiene automáticamente desde el dominio.
    """
    if user_exists(email):
        return False, "El usuario ya existe."

    if role is None:
        role = get_role_from_email(email)

    if role is None:
        return False, "El email no tiene un dominio válido."

    password_hash = hash_password(password)

    try:
        query = f"""
        INSERT INTO Users (email, password_hash, role)
        VALUES ('{email}', '{password_hash}', '{role}');
        """
        execute_query(query)
        return True, "Usuario creado correctamente."
    except Exception as e:
        return False, f"Error al crear usuario: {e}"



# ==========================================================
# AUTENTICACIÓN
# ==========================================================

def authenticate(email: str, password: str):
    """
    Verifica login:
    - Comprueba que el usuario existe
    - Compara su contraseña
    - Devuelve (True, "rol") si es correcto
    - Devuelve (False, motivo) si falla
    """
    user = get_user(email)
    if not user:
        return False, "Usuario no encontrado."

    if not verify_password(password, user["password_hash"]):
        return False, "Contraseña incorrecta."

    return True, user["role"]
