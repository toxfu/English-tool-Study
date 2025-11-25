import streamlit as st
import json
from pathlib import Path


def user_preferences():
    """
    Crea un archivo de configuración para la aplicación Streamlit.
    Si el archivo ya existe, carga la configuración existente.
    """
    preferences_path = Path("utils/user_preferences.json")
    if preferences_path.exists():
        st.session_state.config_done = True
        st.rerun()
    
    else:
        st.title("🔧 Configuración Inicial")
        st.write("Por favor, introduce los ajustes necesarios para comenzar.")
        with st.form("config_form", clear_on_submit=False):
            model = st.radio(
                "Selecciona un modelo LLM para generar texto",
                ["Qwen/Qwen3-8B-FP8", "Qwen/Qwen3-4B-FP8", "Qwen/Qwen3-1.7B-FP8", "Qwen/Qwen3-0.6B-FP8"],
                captions=[
                    "Ocupa ~10GB de VRAM",
                    "Ocupa ~5GB de VRAM (recomendado)",
                    "Ocupa ~2.5GB de VRAM",
                    "Ocupa ~1GB de VRAM"
                ],
                index=1,
                help="Los modelos pequeños podrían tener problemas para seguir instrucciones, como generar la palabra exacta, y, por lo tanto, tardar más. Los modelos más grandes son mejores siguiendo instrucciones, pudiendo llegar a ser más rápidos. Además al tener vocabulario más amplio, generan textos más ricos y variados. **El modelo Qwen3-4B-FP8 es el que alcanza el mejor equilibrio.**",
            )
            voice = st.pills("Voz", ["femenina", "masculina"], default="femenina")
            
            config = {
                "model": model,
                "voice": voice,
            }
            submitted = st.form_submit_button("Guardar configuración")
            if submitted:
                preferences_path.write_text(json.dumps(config, indent=2))
                st.session_state.config_done = True
                st.success("¡Configuración guardada con éxito!")
                st.rerun()