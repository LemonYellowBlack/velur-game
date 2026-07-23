from textwrap import dedent
from anthropic.types import MessageParam
from config import (
    NARRATOR_MODEL,
    NARRATOR_SYSTEM_PROMPT,
    DIRECTOR_MODEL,
    DIRECTOR_SYSTEM_PROMPT,
    MAX_TOKENS,
)
from domain import (
    Game,
    Turn,
    StoryState,
    NarrationError,
    DirectionError,
)
from rules import get_exhaustion


def get_turn_header(g: Game) -> str:
    return dedent(f"""
                    NARRATIVE DIRECTION:
                    tension: {g.story_state_log[-1].tension.cue}
                    pace: {g.story_state_log[-1].pace.cue}
                    danger: {g.story_state_log[-1].danger.cue}
                    mood: {g.story_state_log[-1].mood.cue}
                    player exhaustion: {get_exhaustion(g.player_stats.stamina).cue}
                    ------------------------------------
                  """)


def get_director_header(g: Game) -> str:
    return dedent(f"""
                    PREVIOUS DIRECTION:
                    tension: {g.story_state_log[-1].tension}
                    pace: {g.story_state_log[-1].pace}
                    danger: {g.story_state_log[-1].danger}
                    mood: {g.story_state_log[-1].mood}
                    ------------------------------------
                  """)


def build_turn_message(g: Game) -> list[MessageParam]:
    messages = list(g.messages)
    if messages and messages[-1]["role"] == "user":
        content = messages[-1]["content"]
        if not isinstance(content, str):
            return messages

        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": get_turn_header(g)},
                {"type": "text", "text": content},
            ],
        }

    return messages


def build_director_message(g: Game) -> list[MessageParam]:
    messages = list(g.messages)
    if messages and messages[-1]["role"] == "user":
        content = messages[-1]["content"]
        if not isinstance(content, str):
            return messages

        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": get_director_header(g)},
                {"type": "text", "text": content},
            ],
        }

    return messages


def direct_story(g: Game) -> None:
    try:
        director = g.client.messages.parse(
            model=DIRECTOR_MODEL,
            max_tokens=MAX_TOKENS,
            system=DIRECTOR_SYSTEM_PROMPT,
            messages=build_director_message(g),
            output_format=StoryState,
        )
    except Exception as e:
        raise DirectionError(f"call to director failed: {e}") from e

    story_state = director.parsed_output

    if story_state is None:
        raise DirectionError("no direction returned")

    g.story_state_log.append(story_state)
    print(
        dedent(f"""\n   
            --------------------    
                STORY STATE
            --------------------\n
            rationale: {story_state.rationale}\n
            danger: {story_state.danger}
            mood: {story_state.mood}
            tension: {story_state.tension}
            pace: {story_state.pace}\n
        """)
    )

    return


def get_turn_from_narrator(g: Game) -> Turn:
    try:
        narrator = g.client.messages.parse(
            model=NARRATOR_MODEL,
            max_tokens=MAX_TOKENS,
            system=NARRATOR_SYSTEM_PROMPT,
            messages=build_turn_message(g),
            output_format=Turn,
        )
    except Exception as e:
        raise NarrationError(f"call to narrator failed: {e}") from e

    if narrator.parsed_output is None:
        raise NarrationError("narrator returned None")

    return narrator.parsed_output
