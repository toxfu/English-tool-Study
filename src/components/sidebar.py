import streamlit as st

from tools.llm_tools import translate_to_spanish
from utils.config import DICT_CONN

def dictionary_section():
    st.markdown("## *Enter a word to search for its meaning*")
    word_input = st.text_input("Word")
    
    # Solo ejecutar si el input cambió
    if word_input and word_input != st.session_state.get("last_dict_word"):
        st.session_state.last_dict_word = word_input
        df = DICT_CONN.query(
            "SELECT * FROM entries WHERE word = :word",
            params={"word": word_input}
        )
        if df.empty:
            st.session_state.dictionary_result = "No results found"
        else:
            definitions = [d.replace("\n", "") for d in df["definition"].tolist()]
            st.session_state.dictionary_result = "🔹 " + "\n🔹 ".join(definitions)
    
    # Mostrar resultados almacenados
    if "dictionary_result" in st.session_state:
        st.text_area("Definitions", 
                    value=st.session_state.dictionary_result, 
                    height=150, disabled=True)

def translation_section():
    st.markdown("## *Translate to Spanish*")
    translation_input = st.text_area("Phrase")
    
    # Solo ejecutar si el input de traducción cambió
    if translation_input and translation_input != st.session_state.get("last_translation_phrase"):
        st.session_state.last_translation_phrase = translation_input
        translation = translate_to_spanish(translation_input)
        st.session_state.translation_result = translation
    
    # Mostrar traducción almacenada
    if "translation_result" in st.session_state:
        st.text_area("Translation Result", 
                    value=st.session_state.translation_result, 
                    height=150, disabled=True)

def sidebar():
    with st.sidebar:
        dictionary_section()
        translation_section()