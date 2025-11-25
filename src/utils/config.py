import torch
from sqlalchemy.orm import declarative_base
import json
from pathlib import Path
from datetime import datetime, timezone
from enum import IntEnum
import streamlit as st
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForCausalLM
)
from kokoro import KPipeline
import spacy


# cargar los parametros de user_preferences.json
# Ruta relativa desde la raíz del proyecto


try:
    nlp = spacy.load("en_core_web_md")
except Exception as e:
    spacy.cli.download("en_core_web_md")
    nlp = spacy.load("en_core_web_md")


CURRENT_DIR = Path(__file__).resolve()

PREFERENCES_PATH = Path(CURRENT_DIR.parent / "user_preferences.json")
print(PREFERENCES_PATH.resolve())   

def load_user_preferences():
    if PREFERENCES_PATH.exists():
        with PREFERENCES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "model": data.get("model", "Qwen/Qwen3-4B-FP8"),
                "voice": data.get("voice", "femenina")
            }


pref = load_user_preferences()

MODEL_NAME = pref["model"]

if VOICE := pref["voice"] == "femenina":
    VOICE = "af_heart"
else:
    VOICE = "am_adam"


Base = declarative_base()

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
@st.cache_resource
def load_base_resources():
    return {
        "dict_conn": st.connection("dictionary_db"),
        "dict_translator": pipeline(
            "translation",
            model="Helsinki-NLP/opus-mt-en-es",
            device=DEVICE,
            # dtype=torch.float8_e4m3fn,
            dtype =torch.float16,
        ),
        # text section
        "text_model": AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            device_map="cuda:0",
            trust_remote_code=True,
            dtype =torch.float16,
            # dtype=torch.float8_e4m3fn,
        ),
        "text_tokenizer": AutoTokenizer.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True,
            padding_side="left",
        ),
        "audio_pipeline": KPipeline(lang_code='a', device=DEVICE)
    }

_resources = load_base_resources()

# Sidebar resources
DICT_CONN = _resources["dict_conn"]
DICT_TRANSLATOR = _resources["dict_translator"]
# LLMs resources
AUDIO_PIPELINE = _resources["audio_pipeline"]
TEXT_MODEL = _resources["text_model"]
TEXT_TOKENIZER = _resources["text_tokenizer"]


# Cards
DEFAULT_PARAMETERS = (
    0.40255,
    1.18385,
    3.173,
    15.69105,
    7.1949,
    0.5345,
    1.4604,
    0.0046,
    1.54575,
    0.1192,
    1.01925,
    1.9395,
    0.11,
    0.29605,
    2.2698,
    0.2315,
    2.9898,
    0.51655,
    0.6621,
)

DECAY = -0.5
FACTOR = 0.9 ** (1 / DECAY) - 1


class State(IntEnum):
    """
    Enum representing the learning state of a Card object.
    """

    Learning = 1
    Review = 2
    Relearning = 3


class Rating(IntEnum):
    """
    Enum representing the four possible ratings when reviewing a card.
    """
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

INITIAL_CARDS_VALUES = {
    "last_review": None,
    "review_datetime": None,
    "days_since_last_review": None,
    "due": datetime.now(timezone.utc),
    "stability": 1.18385,
    "difficulty": 6.488305,
    "state": State.Learning,
    "rating": Rating.Hard,
    "step": 1
}