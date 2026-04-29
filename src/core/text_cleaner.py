import re

DEFAULT_FILLERS = ["um", "uh"]

def clean_text(raw_text: str, config=None):
    """
    clean raw transcript text.

    Args:
        raw_text: The raw transcript string
        config: Optional project config dictionary
    
    Returns:
        A cleaned transcript string
    
    Raises:
        TypeError: If raw_text is not a string
        ValueError: If cleaned text is empty and empty text is not allowed
    """

    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")

    remove_bracket_tags = True
    remove_fillers = True
    fillers = DEFAULT_FILLERS
    allow_empty_text = False

    if config is not None:
        transcript_config = config.get("transcript", {})

        remove_bracket_tags = transcript_config.get("remove_bracket_tags", True)
        remove_fillers = transcript_config.get("remove_fillers", True)
        fillers = transcript_config.get("fillers", DEFAULT_FILLERS)
        allow_empty_text = transcript_config.get("allow_empty_text", False)
    
    text = raw_text.strip()

    if remove_bracket_tags:
        text = re.sub(r'\[.*?\]', '', text)

    text = re.sub(r'\s+', ' ', text)

    if remove_fillers:
        words = text.split()
        cleaned_words = []

        for word in words:
            normalized_word = word.lower().strip(".,!?")
            if normalized_word not in fillers:
                cleaned_words.append(word)
        
        text = " ".join(cleaned_words)
    
    text = text.strip()

    if not allow_empty_text and not text:
        raise ValueError("cleaned text cannot be empty")

    return text