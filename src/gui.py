import streamlit as st

def max_width(percent_width:int = 60):
    max_width_str = f"max-width: {percent_width}%;"
    st.markdown(f"""
                <style>
                .stMainBlockContainer{{{max_width_str}}}
                </style>
                """,
                unsafe_allow_html=True,
    )

def main():
    tab1, tab2, tab3 = st.tabs(["🎓 Study", "🛢️ Database", "🦉 Free Study"])
    with tab1:
        study_section()
    with tab2:
        database_section()
    with tab3:
        free_study()

#todo: cambiar los user_preferences.json

if __name__ == "__main__":
    with open("assets/style.css") as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)
    if "config_done" not in st.session_state:
        st.session_state.config_done = False
    if not st.session_state.config_done:
        from components.parameters_page import user_preferences
        user_preferences()
    else:
        # tools
        from components.sidebar import sidebar
        from components.study_section import study_section
        from components.database_section import database_section
        from components.free_study import free_study
        max_width()
        sidebar()
        main()