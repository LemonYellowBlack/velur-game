from pathlib import Path
from textwrap import dedent

NARRATOR_MODEL = "claude-haiku-4-5"
NARRATOR_SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
NARRATOR_MAX_TOKENS = 1024
FIRST_TURN = "Begin a new adventure with a castle scene."

DIRECTOR_MODEL = "claude-sonnet-4-6"
DIRECTOR_SYSTEM_PROMPT = dedent("""
    You are the Director of a dark fantasy adventure, responsible for shaping the story's arc over time.
    Read the story and set tension, pace, danger, and mood for the next beat.
    A story must breathe: build tension toward peaks and release afterward. 
    Escalate or lower stakes to keep the story moving.
    """)
DIRECTOR_MAX_TOKENS = 1024

LOREMASTER_MODEL = "claude-sonnet-5"
LOREMASTER_SYSTEM_PROMPT = dedent("""
    You are the Director of a dark fantasy adventure, responsible for shaping the story's arc over time.
    Read the story and set tension, pace, danger, and mood for the next beat.
    A story must breathe: build tension toward peaks and release afterward. 
    Escalate or lower stakes to keep the story moving.
    """)
LOREMASTER_MAX_TOKENS = 1024

SAVES_DIR = Path(__file__).parent / "saves"
