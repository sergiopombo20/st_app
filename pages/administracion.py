import streamlit as st
import pandas as pd
from utils.auth import create_user, get_user, hash_password
from utils.db import run_query, execute_query


# ==========================================================
# RESTRICCIÓN DE ACCESO
# ==========================================================
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("Debe iniciar sesión para acceder a esta página.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("Acceso denegado. Solo administradores pueden ver esta página.")
    st.stop()


# ==========================================================
# TÍTULO
# ==========================================================
st.title("Panel de Administración")
st.markdown("Gestión de usuarios, roles y contraseñas.")


# ==========================================================
# SECCIÓN 1 — LISTADO DE USUARIOS
# ==========================================================
st.subheader("Usuarios registrados")

df_users = run_query("SELECT email, role FROM Users ORDER BY role, email;")

if df_users.empty:
    st.info("No hay usuarios registrados.")
else:
    st.dataframe(df_users, use_container_width=True)


st.divider()


# ==========================================================
# SECCIÓN 2 — CREAR NUEVO USUARIO
# ==========================================================
st.subheader("Crear nuevo usuario")

with st.form("create_user_form", clear_on_submit=True):
    email = st.text_input("Email del nuevo usuario")
    password = st.text_input("Contraseña inicial", type="password")
    role = st.selectbox("Rol", ["admin", "direccion", "expansion", "rrhh"])

    submitted = st.form_submit_button("Crear usuario")

    if submitted:
        if not email or not password:
            st.error("Debe completar todos los campos.")
        else:
            ok, msg = create_user(email, password, role)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)



st.divider()


# ==========================================================
# SECCIÓN 3 — RESET DE CONTRASEÑA
# ==========================================================
st.subheader("Restablecer contraseña a un usuario existente")

with st.form("reset_password_form", clear_on_submit=True):
    email_reset = st.text_input("Email del usuario a restablecer")
    new_password = st.text_input("Nueva contraseña", type="password")

    submitted = st.form_submit_button("Restablecer contraseña")

    if submitted:
        user = get_user(email_reset)

        if not user:
            st.error("El usuario no existe.")
        else:
            new_hash = hash_password(new_password)

            try:
                query = f"""
                UPDATE Users 
                SET password_hash = '{new_hash}' 
                WHERE email = '{email_reset}';
                """
                execute_query(query)
                st.success("Contraseña restablecida correctamente.")
            except Exception as e:
                st.error(f"Error al actualizar contraseña: {e}")
