from typing import List, Tuple
from transformers import GenerationConfig, TextIteratorStreamer
import torch
from threading import Thread

from utils.config import DEVICE, DICT_TRANSLATOR, AUDIO_PIPELINE, TEXT_MODEL, TEXT_TOKENIZER, VOICE
from tools.sql_tool import Deck

class Chatbot:
    def __init__(self):
        self.tokenizer = TEXT_TOKENIZER
        self.model = TEXT_MODEL
        self.history = []
        self.summary = []
        self.default_instructions = """You are an English tutor who helps users improve their English through conversation.

Your rules:
1. If the user makes a grammar, spelling, or phrasing mistake in English, **first correct it clearly and briefly**.
2. After correcting, reply naturally to the user’s message and **continue the conversation**.
3. Keep your replies **short, direct, and useful** — avoid unnecessary explanations unless asked.
4. Focus on practical, real-life English.

Always prioritize clarity and efficiency.
"""
        
    def set_instructions(self, instructions: str | None) -> None:
        """
        Agrega instrucciones al prompt del chatbot.
        
        :param instructions: Instrucciones a agregar al prompt.
        """
        if instructions is None:
            instructions = self.default_instructions
        self.history = [{"role": "system", "content": instructions}]
        self.summary = [{"role": "system", "content": instructions}]
    
    def _summarize(self):
        messages_to_summarize = self.summary[1:]
        
        # Crear prompt para resumir
        conversation_text = "".join(
            f"{msg['role']}: {msg['content']}\n" for msg in messages_to_summarize)
        
        summary_prompt = f"""
        Summarize this English tutoring conversation in 2-3 sentences. Focus on:
        - Key topics discussed
        - Main grammar/vocabulary corrections made
        - Student's progress or recurring issues
        
        Conversation:
        {conversation_text}
        
        Summary:
        """
        summary_template = self.tokenizer.apply_chat_template(
            summary_prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        # Generar resumen
        inputs = self.tokenizer(summary_template, return_tensors="pt").to(DEVICE)
        
        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                do_sample=True,
                temperature=0.3
            )
            summary = self.tokenizer.decode(
                output_ids[0][len(inputs.input_ids[0]):],
                skip_special_tokens=True
            )
            summary = summary.split("<think>")[-1].strip()
        # Agregar resumen como mensaje del sistema
        summary_msg = {
            "role": "system", 
            "content": f"[Conversation Summary]: {summary}"
        }
        self.summary = [self.summary[0]]
        self.summary.append(summary_msg)
        
    def generate_response(self, user_input):
        # check if prompt is set, if not, set default instructions
        if not self.history:
            self.set_instructions(None)

        # Agregar nuevo mensaje de usuario al historial
        self.history.append({"role": "user", "content": user_input})
        self.summary.append({"role": "user", "content": user_input})
        # Preparar el prompt completo
        text = self.tokenizer.apply_chat_template(
            self.summary,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        # Tokenizar entrada
        inputs = self.tokenizer(text, return_tensors="pt").to(DEVICE)
        # Configurar streamer
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        # Generar respuesta en un hilo separado
        generation_thread = Thread(
            target=self.model.generate,
            kwargs={
                **inputs,
                "streamer": streamer,
                "max_new_tokens": 200
            }
        )
        generation_thread.start()
        # Stream tokens
        response = ""
        for token in streamer:
            response += token
            yield token
        # Agregar respuesta completa al historial
        self.history.append({"role": "assistant","content": response})
        self.summary.append({"role": "assistant", "content": response})
        self._summarize()

    def create_conversation_markdown(self):
        """
        Crea un string en formato Markdown a partir de history,
        que es lista de dicts con keys "role" y "content".
        """
        md_lines = ["# Historial de la conversación\n"]
        for msg in self.history:
            role = msg.get("role", "")
            if role == "assistant":
                # Añadir emoji de asistente
                role = "🤖 Assistant"
            elif role == "user":
                # Añadir emoji de usuario
                role = "🗣️ User"
            else:
                role = "📋 System message"
            content = msg.get("content", "")
            content = str(content)
            # Encabezado de nivel 2 con el rol
            md_lines.append(f"## {role}")
            md_lines.append(content)
            md_lines.append("")  # línea en blanco de separación
        return "\n".join(md_lines)
    
    def retrieve_history(self):
        return self.history[1:]


def calculate_token_settings(text_length: str, remaining_list: List[List]) -> Tuple[int, List[str]]:
    """Return max_tokens and words_interval based on length and group size."""
    TEXT_LENGTH_TOKENS = {
        "short": 100,
        "medium": 130,
        "long": 160
    }
    num_words_list = [len(group) for group in remaining_list]
    
    base_tokens = TEXT_LENGTH_TOKENS.get(text_length, 100)
    max_tokens = [max(100, int(round(base_tokens * num_words / 5))) for num_words in num_words_list]

    min_words = [max_token // 2 for max_token in max_tokens]
    max_words = [int(max_token / 1.5) for max_token in max_tokens]
    words_interval = [f"{min_word} - {max_word} words" for min_word, max_word in zip(min_words, max_words)]
    num_tokens = max(max_tokens)

    return num_tokens, words_interval


def generate_text(topic: str,
                  grouped_cards: List[List[Deck]],
                  temperature: float,
                  text_length: str
                  ) -> Tuple[List[List[str]], List[List[Deck]], List[str]]:
    """
    Genera un texto breve a partir de una lista de palabras clave.

    :param text_pipeline: Pipeline de generación de texto.
    :param topic: Tema del texto.
    :param words_list: Lista de listas de palabras clave.
    """
    
    remaining_list = [[entry.word for entry in group] for group in grouped_cards]
    num_tokens, words_interval = calculate_token_settings(text_length, remaining_list)
    gen_config = GenerationConfig(
            max_new_tokens=num_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.95,
            repetition_penalty=1.15,
            pad_token_id=TEXT_TOKENIZER.eos_token_id,
            eos_token_id=TEXT_TOKENIZER.eos_token_id
    )
    # Extraer solo las palabras de cada grupo
    
    texts = []
    reordered_words = []
    reordered_cards = []
    
    while True:
        if len(remaining_list) == 0:
            break
        prompts = [
            (
                f"Generate a short paragraph ({words_interval}) about {topic} that MUST include "
                f"these EXACT words: {', '.join(words)}!"
                "Do NOT use derivatives, variations, or related forms. "
                "Example: If the word is 'run', don't use 'running' or 'ran'. "
                "Write in simple English. Output ONLY the paragraph."
            )
            for words, words_interval in zip(remaining_list, words_interval)
        ]
        messages = [[{"role": "user", "content": p}] for p in prompts]
        chat_templates = [
            TEXT_TOKENIZER.apply_chat_template(
                message,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False
            ) for message in messages
        ]
        with torch.inference_mode():
            # 2. Tokeniza todo en batch
            inputs = TEXT_TOKENIZER(
                chat_templates,
                return_tensors="pt",
                padding=True,
                truncation=True
            ).to(DEVICE)
            output_ids = TEXT_MODEL.generate(
                **inputs,
                generation_config=gen_config
            )
            # 4. Decodifica los resultados
            generated_texts = TEXT_TOKENIZER.batch_decode(
                output_ids,
                skip_special_tokens=True
            )
            generated_texts = [generated_text.split("</think>")[-1].strip()
                               for generated_text in generated_texts]
            to_remove = []
            
            for i, (cards, words, text) in enumerate(
                zip(grouped_cards, remaining_list, generated_texts)
            ):
                if all(word.lower() in text.lower() for word in words):
                    texts.append(text)
                    reordered_words.append(words)
                    reordered_cards.append(cards)
                    to_remove.append(i)
            # Eliminar después de iterar (en orden inverso para no desordenar los índices)
            for i in sorted(to_remove, reverse=True):
                del remaining_list[i]
                del words_interval[i]
                del grouped_cards[i]
    return reordered_words, reordered_cards, texts


def generate_audio(texts: str):
    """
    Genera un audio a partir de un texto.

    :param text: Texto a convertir en audio.
    """
    generator = AUDIO_PIPELINE(
            texts, voice=VOICE,
            speed=1, split_pattern=None
    )
    return [next(generator)[2].cpu().numpy() for _ in texts]

def translate_to_spanish(text:str):
    return DICT_TRANSLATOR(text)[0]["translation_text"]