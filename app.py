import streamlit as st
import os
from utils.auth import authenticate


# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(page_title="Login", layout="wide")

logo_path = os.path.join("logo", "logo.png")

if os.path.exists(logo_path):
    st.image(logo_path, width=120)


# ==========================================================
# FUNCIÓN PARA CERRAR SESIÓN
# ==========================================================
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ==========================================================
# VERIFICAR SI YA HAY SESIÓN INICIADA
# ==========================================================
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    role = st.session_state["role"]

    st.sidebar.success(f"Conectado como: {st.session_state['email']} ({role})")

    if st.sidebar.button("Cerrar sesión"):
        logout()

    # ==========================================================
    # REDIRECCIÓN A PÁGINAS SEGÚN ROL
    # ==========================================================

    if role == "admin":
        st.title("Panel de Administración")
        st.write("Use el menú de la izquierda para navegar:")
        st.write("➡ Administración (crear usuarios)")
        st.write("➡ Panel de Dirección")
        st.write("➡ Panel de Expansión")

        st.sidebar.header("Páginas disponibles")
        st.sidebar.page_link("pages/administracion.py", label="Administración")
        st.sidebar.page_link("pages/direccion.py", label="Dirección")
        st.sidebar.page_link("pages/expansion.py", label="Expansión")

    elif role == "direccion":
        st.title("Panel de Dirección")
        st.sidebar.page_link("pages/direccion.py", label="Acceder al Panel")

    elif role == "expansion":
        st.title("Panel de Expansión")
        st.sidebar.page_link("pages/expansion.py", label="Acceder al Panel")

    else:
        st.error("Rol desconocido. Contacte con un administrador.")
        logout()

    st.stop()



# ==========================================================
# SI NO HAY SESIÓN → MOSTRAR LOGIN
# ==========================================================
st.title("Inicio de Sesión")

with st.form("login_form"):
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    submitted = st.form_submit_button("Iniciar sesión")

    if submitted:
        ok, result = authenticate(email, password)

        if ok:
            # Guardar sesión
            st.session_state["logged_in"] = True
            st.session_state["email"] = email
            st.session_state["role"] = result  

            st.success("Inicio de sesión correcto. Redirigiendo...")
            st.rerun()
        else:
            st.error(result)
