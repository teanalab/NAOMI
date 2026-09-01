import re

def remove_semantic_repetition(text: str) -> str:
    """
    Finds and removes blocks of repeated sentences from the end of a text.

    This function is designed to clean up LLM outputs where the model gets
    stuck in a loop and repeats a sequence of sentences, either fully or
    partially. It works by identifying if a sequence of sentences at the end
    of the text is a repetition of a sequence that appeared earlier.

    It does not rely on any specific delimiter or tag.

    Args:
        text: The input string to be processed.

    Returns:
        A new string with the final repetitive block removed. If no repetition
        is found, the original text is returned.
    """
    # This regex finds all sequences of characters that end with a period,
    # question mark, or exclamation mark. It's designed to capture full sentences.
    # The '?P<sentence>' part creates a named group for the sentence text.
    # The '?P<space>' part captures any trailing whitespace (like newlines).
    sentence_pattern = r'(?P<sentence>.+?[.?!])(?P<space>\s*)'
    
    # Use re.finditer to get match objects, which preserve more info.
    # We strip each sentence for a clean comparison, but store the original
    # sentence with its trailing space for perfect reconstruction.
    matches = [
        {'clean': m.group('sentence').strip(), 'original': m.group(0)}
        for m in re.finditer(sentence_pattern, text, re.DOTALL)
    ]

    if len(matches) < 2:
        # Not enough sentences to have a repetition.
        return text

    # We are looking for the point 'i' where the text after it is a repetition
    # of the text at the beginning. We iterate from the start of the text.
    # 'i' is the potential start of the *repeated* block.
    for i in range(1, len(matches)):
        # 'original_block' is the part of the text that might be repeated.
        original_block = [m['clean'] for m in matches[:i]]
        
        # 'repeated_block' is the part at the end that we suspect is a repetition.
        repeated_block = [m['clean'] for m in matches[i:]]

        # Check if the repeated_block is a prefix of the original_block.
        # This handles both full and partial repetitions.
        # e.g., original=[A,B,C], repeated=[A,B] -> True
        # e.g., original=[A,B], repeated=[A,B] -> True
        if original_block[:len(repeated_block)] == repeated_block:
            # We found a repetition! The correct text is the first block.
            # We reconstruct it from the original matches to preserve spacing.
            correct_matches = matches[:i]
            return "".join(m['original'] for m in correct_matches).strip()

    # If the loop finishes, no repetition was found.
    return text



def reomove_repetition(response_text: str) -> str:
    """
    Detects if a string is a simple, direct repetition of itself (e.g., "abc abc")
    and returns only the unique part if a repetition is found.
    This version is more robust to minor whitespace differences between the halves.
    """
    cleaned_text = response_text.strip()
    length = len(cleaned_text)

    # Can't be a repetition if it's too short
    if length < 20:
        return response_text

    midpoint = length // 2
    first_half = cleaned_text[:midpoint]
    second_half = cleaned_text[midpoint:]

    # KEY CHANGE: Compare the stripped versions of the halves.
    # This handles cases like ("...goal? ") and ("...goal?") being treated as identical.
    if first_half.strip() == second_half.strip():
        print("[CLEANUP] Repetition detected. Returning the unique, stripped first half.")
        return first_half.strip()
    
    # If no repetition is found, return the original text
    return response_text
