import streamlit as st
from tools.llm_tools import Chatbot


def reset_chat():
    """
    Resets the chat history.
    """
    st.session_state.chatbot = Chatbot()  # Reinicializar el chatbot
    st.rerun()


def free_study():
    st.title("ChatBot")
    # Inicializar chatbot solo una vez
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = Chatbot()

    with st.expander("Chatbot prompt", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.text_area(
                "Default prompt",
                value=st.session_state.chatbot.default_instructions,
                key="default_prompt",
                height=200,
                disabled=True
            )
            if st.button("Restore default prompt"):
                st.session_state.chatbot.set_instructions(instructions=None)

        with col2:
            custom_prompt = st.text_area(
                "Custom prompt",
                height=200,
            )
            if st.button("Use custom prompt"):
                st.session_state.chatbot.set_instructions(instructions=custom_prompt)

    user_message = st.chat_input("Say something")
    retrieved_history = st.session_state.chatbot.retrieve_history()
    
    if user_message is not None or retrieved_history:
        with st.container(height=500, border=True):
            for msg in retrieved_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            if user_message:  # Solo mostrar y procesar si el usuario escribió algo
                with st.chat_message("user"):
                    st.write(user_message)
                with st.chat_message("assistant"):
                    response_generator = st.session_state.chatbot.generate_response(user_message)
                    st.write_stream(response_generator)

    col1, col2 = st.columns([1, 1])
    with col1:
        if retrieved_history:
            md_text = st.session_state.chatbot.create_conversation_markdown()
            st.download_button(
                "Descargar conversación (Markdown)",
                data=md_text,
                file_name="conversation.md",
                mime="text/markdown",
                icon=":material/download:",
            )
        else:
            st.button("Descargar conversación (Markdown)", disabled=True)
    with col2:
        st.button("Reset Chat", on_click=reset_chat)