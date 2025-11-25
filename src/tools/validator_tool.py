from utils.config import nlp

def validate_word(word: str) -> bool:
    # evitar dobles espacios
    word = ' '.join(word.split())
    
    doc = nlp(word)
    # Validamos que cada token importante no sea OOV (fuera del vocabulario)
    return all(token.is_alpha and not token.is_oov for token in doc if not token.is_stop)

def validate_words(words: list) -> list:
    """
    Valida una lista de palabras o words, asegurando que cada una sea válida según las reglas definidas.
    
    :param words: Lista de palabras o words a validar.
    :return: Lista de palabras o words válidas.
    """
    valid_words = []
    invalid_words = []
    for word in words:
        if validate_word(word):
            valid_words.append(word)
        else:
            invalid_words.append(word)
    return valid_words, invalid_words