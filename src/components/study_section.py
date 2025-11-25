import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List

import streamlit as st

from tools.fsrs_scheduler import learning_scheduler
from tools.llm_tools import generate_audio, generate_text
from tools.sql_tool import (
    Deck,
    add_cards,
    deck_selection,
    new_deck_db,
    open_deck,
    update_card,
)
from tools.validator_tool import validate_words
from utils.config import Rating

"""
we have 3 studying sessions states:
- studying_deck
- studying_db

if deck is changed, we need to close the previous db connection and open a new one and reset the next states:
    - study_config:
        - topic
        - group_size
        - temperature
        - text_length

    - phase: config | active | studying
    - batches: (list of Batch)
    - current_index
    - repeat_counter

"""

@st.cache_resource(show_spinner="Opening deck database...")
def study_deck_connection(deck_name: str):
    _, session = open_deck(deck_name)
    return session

class Phase(str, Enum):
    CONFIG = "config"
    ACTIVE = "active"
    STUDYING = "studying"


@dataclass(frozen=True)
class StudyConfig:
    topic: str
    group_size: int
    temperature: float
    text_length: str


@dataclass
class Batch:
    words: list[str]
    cards: list[Deck]
    text: str
    audio: bytes


################################################################################
# ============================ Session state utils ============================ #
################################################################################


def _state():
    s = st.session_state
    defaults = {
        "phase": Phase.CONFIG,
        "batches": [],
        "current_index": 0,
        "repeat_counter": 0,
    }
    for key, value in defaults.items():
        if key not in s:
            s[key] = value
    return s


def reset_session_state(full: bool = False):
    s = _state()
    s.batches = []
    s.current_index = 0
    s.repeat_counter = 0
    if full:
        s.phase = Phase.CONFIG
        s.pop("study_config", None)


###############################################################################
######## ======================= cards section ======================= ########
###############################################################################

def _get_overdue_entries_grouped(session, group_size: int) -> List[List[Deck]]:
    now = datetime.now(timezone.utc)
    results = session.query(Deck).filter(Deck.due < now).all()
    random.shuffle(results)
    # Agrupar de a `group_size` elementos
    return [results[i:i+group_size] for i in range(0, len(results), group_size)]

def build_batches(session, study_config: StudyConfig) -> List[Batch]:
    topic = study_config.topic
    group_size = study_config.group_size
    temperature = study_config.temperature
    text_length = study_config.text_length
    # Obtener tarjetas de la base de datos
    grouped_cards = _get_overdue_entries_grouped(session, group_size)
    reordered_words, reordered_cards, texts = generate_text(topic, grouped_cards, temperature, text_length)
    audios = generate_audio(texts)
    # all together
    batches: list[Batch] = []
    for words, cards, text, audio in zip(
        reordered_words, reordered_cards, texts, audios
    ):
        batches.append(
            Batch(
                words=list(words),
                cards=list(cards),
                text=text,
                audio=audio,
            )
        )
    return batches

def _update_index(delta):
    s = st.session_state
    if s.batches:
        s.current_index = (
            s.current_index + delta
        ) % len(s.batches)

def _delete_actual_element():
    s = st.session_state
    if s.batches:
        current_index = s.current_index
        # Eliminar el elemento actual
        del s.batches[current_index]
        # Ajustar el índice si es necesario
        new_length = len(s.batches)
        if new_length > 0:
            s.current_index = min(current_index, new_length - 1)
        else:
            s.current_index = 0

def _handle_rating(key):
    """Maneja la calificación de una tarjeta"""
    s = st.session_state
    if s.batches and s.current_index < len(s.batches):
        current_cards = s.batches[s.current_index].cards
        update_card_state(current_cards, key=key)
        _delete_actual_element()

def update_card_state(current_cards, key):
    s = st.session_state
    # Actualizar la tarjeta con el nuevo estado
    keys = {"again": Rating.Again, "easy": Rating.Easy, "good": Rating.Good, "hard": Rating.Hard}
    rating_key = keys[key]
    for card in current_cards:
        new_values_card = learning_scheduler(
            state = card.state,
            stability = card.stability,
            difficulty = card.difficulty,
            rating = rating_key,
            days_since_last_review = card.days_since_last_review,
            review_datetime = card.review_datetime,
            last_review = card.last_review,
            step = card.step, 
        )
        update_card(
            st.session_state.studying_db,
            word = card.word,
            last_review = new_values_card[0],
            review_datetime = new_values_card[1],
            days_since_last_review = new_values_card[2],
            due = new_values_card[3],
            stability = new_values_card[4],
            difficulty = new_values_card[5],
            state = new_values_card[6],
            rating = new_values_card[7],
            step = new_values_card[8]
        )
    if key == "again":
        s.repeat_counter += 1


def render_cards(study_config: StudyConfig, state):
    s = state
    
    # Cargar tarjetas solo si no están en el estado o es nueva fase
    if s.phase == Phase.ACTIVE:
        # Obtener tarjetas de la base de datos
        s.batches = build_batches(
            s.studying_db,
            study_config
        )
        s.phase = Phase.STUDYING

    cards_len = len(s.batches)
    # Si no hay tarjetas y no tenemos un contador de repeticiones
    # significa que hemos terminado la sesión de estudio
    if cards_len == 0:
        if s.repeat_counter == 0:
            st.success("You've finished your study session for now, congratulations! 🎉")
        else:
            st.success("Continue with the review 💪🏻")
            if st.button("Review Again"):
                s.repeat_counter = 0
                s.phase = Phase.ACTIVE
                st.rerun()
        return
    
    current_index = s.current_index
    current_group = s.batches[current_index]
    current_words, current_cards, text, audio = current_group.words, current_group.cards, current_group.text, current_group.audio
    
    # Botones de navegación
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            st.button("←", on_click=_update_index, args=(-1,), key="prev")

        with col3:
            st.button("→", on_click=_update_index, args=(1,), key="next")

        # Mostrar contenido central
        with col2:
            st.markdown(f"#### Words to learn: ***{' - '.join(current_words)}***")
            st.markdown("---")
            st.markdown(f"*{text}*")
            st.audio(audio, sample_rate=24000)
            st.progress((current_index + 1)/cards_len)
            
            rating_keys = ["again", "easy", "good", "hard"]
            cols = st.columns(len(rating_keys))

            for i, key in enumerate(rating_keys):
                with cols[i]:
                    st.button(
                        key.capitalize(), 
                        on_click=_handle_rating, 
                        args=(key,), 
                        key=key
                    )


################################################################################
# ================================ UI Panels ================================== #
################################################################################


def db_panel(state):
    s = state
    with st.expander("Create or select a database", icon=":material/database:"):
        col1, col2 = st.columns([2,3])
        with col1:
            st.write("Enter Database Name")
            db_name = st.text_input("Database Name")
            if st.button("Create Database"):
                new_deck_db(db_name)
                st.success(f"Database {db_name} created")

        with col2:
            current_deck = s.get("studying_deck")
            st.write("Select Database")
            db_files = deck_selection()
            deck = st.selectbox(
                "Select a deck",
                options=db_files
            )
            if deck:
                if deck != current_deck:
                    # limpieza de la base de datos anterior
                    if s.get("studying_db") is not None:
                        s.get("studying_db").close()
                    s.studying_deck = deck
                    s.studying_db = study_deck_connection(deck)
                    reset_session_state(full=True)
                st.write(f"Deck activo: {deck}")


def render_add_words_panel(state):
    s = state
    with st.expander("Add words to the database", icon=":material/history_edu:"):
        st.write("add words or phrases separated by commas")
        user_input = st.chat_input(placeholder="word1, word2, phrase1, phrase2")
        if user_input:
            words = [word.strip() for word in user_input.split(',')]
            # Validar las palabras ingresadas
            valid_words, invalid_words = validate_words(words)
            if invalid_words:
                st.error(f"Invalid words: {', '.join(invalid_words)}, please check the spelling or format.")
            if valid_words:
                add_cards(s.studying_db, words=valid_words)
                st.success("Words successfully added")


def render_config_panel(state):
    s = state
    with st.expander("Start studying the words", icon=":material/book:", expanded=True):
        st.markdown(f"Database: **{s.studying_deck}**")
        st.markdown("---")
        st.markdown("### Select your study parameters")

        with st.form("study_config_form", clear_on_submit=False):
            topic = st.text_input(
                "Enter a topic for the text generation",
                value="Fantasy",
            )
            group_size = st.slider(
                "Select group size", 1, 10, 5, format="%d",
                help="Agrupa varias palabras para generar el texto",
            )
            temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1, format="%.1f",
                help="Higher values make responses more creative."
                    " With very high values, smaller models may struggle"
                    " to follow instructions.",
            )
            text_length = st.pills("Select text length generation", ["short", "medium", "long"], selection_mode="single", default="short"
            )
            submitted = st.form_submit_button("Start Studying")

        if submitted:
            config = StudyConfig(
                topic=topic.strip() or "General",
                group_size=group_size,
                temperature=temperature,
                text_length=text_length,
            )
            s.study_config = config
            reset_session_state(full=False)
            s.phase = Phase.ACTIVE
            st.rerun()


def render_studying_session(state):
    s = state
    render_cards(study_config=s.study_config, state=s)
    if st.button("Restart Study"):
        reset_session_state(full=True)
        st.rerun()

###############################################################################
######## ======================= Main section ======================= #########
###############################################################################

def study_section():
    s = _state()
    db_panel(state = s)
    if "studying_db" not in s:
        return
    render_add_words_panel(state = s)
    if s.phase == Phase.CONFIG:
        render_config_panel(state = s)
    else:
        render_studying_session(state = s)