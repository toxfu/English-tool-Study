import os
import pandas as pd
import streamlit as st

from tools.sql_tool import open_deck, deck_selection, update_card, get_card
from components.study_section import study_deck_connection

@st.cache_resource(show_spinner="Opening deck database...")
def manage_deck_connection(deck_name: str):
    db_path, session = open_deck(deck_name)
    return db_path, session

def database_section():
    st.write("Select Database")
    db_files = deck_selection()
    deck = st.selectbox(
        "Select a deck to manipulate",
        options=db_files
    )
    if deck:
        if deck != st.session_state.get("manage_deck"):
            if "manage_db" in st.session_state and st.session_state.manage_deck is not None:
                st.session_state.manage_db.close()
            st.session_state.manage_deck = deck
            db_path, session = manage_deck_connection(deck)
            st.session_state.db_path_to_delete = db_path
            st.session_state.manage_db = session

        st.write(f"Deck activo: {deck}")
        st.markdown("---")
    
    if "manage_db" in st.session_state:
        # search word section
        st.write("Search word")
        user_query = st.text_input("Search for a word")
        user_query = user_query.strip()
        # Check if the word exists (case-sensitive)
        cards, card_names = get_card(st.session_state.manage_db, user_query)
        if card_names:
            card_name = st.selectbox("Select a matching word", card_names)
            card_index = card_names.index(card_name)
            if card_name:
                card = cards[card_index]
                st.write(f"Word: {card.word}")
                df = pd.DataFrame(
                    [{"overwrite_word": "",
                        "last_review": card.last_review,
                        "review_datetime": card.review_datetime,
                        "days_since_last_review": card.days_since_last_review,
                        "due": card.due,
                        "stability": card.stability,
                        "difficulty": card.difficulty,
                        "state": card.state,
                        "rating": card.rating,
                        "step": card.step}])
                
                st.data_editor(
                    df,
                    column_config={
                        "overwrite_word": st.column_config.TextColumn(
                            "⚠️Overwrite Word",
                            help="Change the word",
                            max_chars=50,
                            validate=r"^st\.[a-z_]+$"
                            ),
                        "last_review": "last review",
                        "review_datetime": "review datetime",
                        "days_since_last_review": "days since last review"
                    },

                    hide_index=True,
                    disabled=["last_review", "review_datetime", "days_since_last_review", "due", "stability", "difficulty", "state", "rating", "step"],
                )
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Overwrite Word"):
                        new_word = df.at[0, "overwrite_word"]
                        update_card(st.session_state.manage_db, card.word, new_word=new_word)
                        manage_deck_connection.clear()
                        st.rerun()
                with col2:
                    if st.button("Reset All Values"):
                        update_card(st.session_state.manage_db, card.word, restore=True)
                        manage_deck_connection.clear()
                        st.rerun()
                with col3:
                    if st.button("Delete Word"):
                        st.session_state.manage_db.delete(card)
                        st.session_state.manage_db.commit()
                        manage_deck_connection.clear()  # 🔁 Limpia el caché
                        st.rerun()
            else:
                st.warning("No results found")
        else:
            st.warning("No results found")
        
        # delete section
        @st.dialog("⚠️ Confirm deletion")
        def confirm_deletion():
            if st.button("Confirm"):
                if st.session_state.get("studying_db") == st.session_state.get("manage_db"):
                    st.session_state.studying_db.close()
                    del st.session_state.studying_db
                    study_deck_connection.clear()
                    st.session_state.studying_deck = None
                st.session_state.manage_db.close()
                st.session_state.manage_db = None
                st.session_state.delete_db = True
                
                # Delete the database file
                os.remove(st.session_state.db_path_to_delete)
                st.session_state.manage_deck = None
                st.rerun()
        st.markdown("---")
        st.write("Delete the database")
        if st.button("Delete Database", key="delete_db"):
            confirm_deletion()