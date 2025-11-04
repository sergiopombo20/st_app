import streamlit as st
import os

st.set_page_config(page_title="Dashboard empresarial", layout="wide")
logo_path = os.path.join("logo", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=120)
st.title("Panel Principal")
st.markdown("Selecciona un departamento en la barra lateral.")
