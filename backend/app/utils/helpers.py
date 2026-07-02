import re

def guess_table_name(model_name: str) -> str:
    """Guess a database table name based on model name (e.g. User -> users)."""
    return model_name.lower() + "s"

def looks_ungrounded(answer: str) -> bool:
    """Check if the agent response looks ungrounded (missing files/data)."""
    lowered = answer.lower()
    bad_markers = (
        "i don't have access",
        "i do not have access",
        "we don't have access",
        "actual content",
        "simulate",
        "assume",
        "likely part of",
        "appears to be part",
        "model a",
        "model b",
        "provided code snippets"
    )
    return any(marker in lowered for marker in bad_markers)
