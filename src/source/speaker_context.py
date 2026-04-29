def capture_speaker_context(
    name: str,
    credentials: str = "",
    stated_motivations: str = "",
    notes: str = "",
) -> dict:
    """
    Capture speaker context for a source video.

    Args:
        name: Speaker name.
        credentials: Speaker background or credentials.
        stated_motivations: Speaker's stated reason, concern, or motivation.
        notes: Optional extra context.

    Returns:
        A speaker context dictionary.

    Raises:
        TypeError: If any input is not a string.
        ValueError: If name is empty.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    if not isinstance(credentials, str):
        raise TypeError("credentials must be a string")

    if not isinstance(stated_motivations, str):
        raise TypeError("stated_motivations must be a string")

    if not isinstance(notes, str):
        raise TypeError("notes must be a string")
    
    cleaned_name = name.strip()

    if not cleaned_name:
        raise ValueError("name cannot be empty")

    return {
        "name": cleaned_name,
        "credentials": credentials.strip(),
        "stated_motivations": stated_motivations.strip(),
        "notes": notes.strip(),
    }