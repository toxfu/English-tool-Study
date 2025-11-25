from sqlalchemy import create_engine, String, Column, Integer, DateTime, Float, Enum
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from typing import List

from utils.config import Base, State, Rating, INITIAL_CARDS_VALUES


class Deck(Base):
    __tablename__ = "deck"
    id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, index=True)
    last_review = Column(DateTime)
    review_datetime = Column(DateTime)
    days_since_last_review = Column(Integer)
    due = Column(DateTime)
    stability = Column(Float)
    difficulty = Column(Float)
    state = Column(Enum(State, native_enum=False, create_constraint=True))  # Entero (1, 2, 3)
    rating = Column(Enum(Rating, native_enum=False, create_constraint=True))  # Entero (1, 2, 3,
    step = Column(Integer)

def new_deck_db(deck_name):
    db_path = Path("db") / f"{deck_name}.db"
    if db_path.exists():
        return "deck already exists"
    engine = create_engine(f'sqlite:///{db_path}', echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def open_deck(deck_name):
    db_path = Path("db") / deck_name
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return db_path, session

def add_cards(session, words: List[str]):
    for word in words:
        # Check if the word exists (case-sensitive)
        if not session.query(Deck).filter(Deck.word == word).first():
            card = Deck(word=word,
                        last_review=INITIAL_CARDS_VALUES["last_review"],
                        review_datetime=INITIAL_CARDS_VALUES["review_datetime"],
                        days_since_last_review=INITIAL_CARDS_VALUES["days_since_last_review"],
                        due=INITIAL_CARDS_VALUES["due"],
                        stability=INITIAL_CARDS_VALUES["stability"],
                        difficulty=INITIAL_CARDS_VALUES["difficulty"],
                        state=INITIAL_CARDS_VALUES["state"],
                        rating=INITIAL_CARDS_VALUES["rating"],
                        step=INITIAL_CARDS_VALUES["step"])
            session.add(card)
    session.commit()

def update_card(session, word, last_review=None, review_datetime=None, days_since_last_review=None, due=None, stability=None, difficulty=None, state=None, rating=None, step=None, new_word=None, restore=False):
    # Check if the word exists (case-sensitive)
    card = session.query(Deck).filter(Deck.word == word).first()
    if card:
        if restore:
            # Restore the card to its initial state
            card.last_review = INITIAL_CARDS_VALUES["last_review"]
            card.review_datetime = INITIAL_CARDS_VALUES["review_datetime"]
            card.days_since_last_review = INITIAL_CARDS_VALUES["days_since_last_review"]
            card.due = INITIAL_CARDS_VALUES["due"]
            card.stability = INITIAL_CARDS_VALUES["stability"]
            card.difficulty = INITIAL_CARDS_VALUES["difficulty"]
            card.state = INITIAL_CARDS_VALUES["state"]
            card.rating = INITIAL_CARDS_VALUES["rating"]
            card.step = INITIAL_CARDS_VALUES["step"]
        else:
            if new_word:
                card.word = new_word
            else:
                card.last_review = last_review
                card.review_datetime = review_datetime
                card.days_since_last_review = days_since_last_review
                card.due = due
                card.stability = stability
                card.difficulty = difficulty
                card.state = state
                card.rating = rating
                card.step = step
    else:
        print(f"Card with word '{word}' not found.")
    session.commit()        

def get_card(session, search_input):
    # recuperar todas las coincidencias que contenga esa palabra
    matches = (
        session
        .query(Deck)
        .filter(Deck.word.ilike(f"%{search_input}%"))
        .order_by(Deck.word)
        .all()
    )
    cards = matches
    card_names = [card.word for card in matches]
    return cards, card_names

def deck_selection():
    # retrieve files from db folder
    db_folder = Path("db")
    db_files = [f.name for f in db_folder.glob("*.db")]
    return db_files