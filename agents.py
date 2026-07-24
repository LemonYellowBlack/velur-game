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
from rules import get_exhaustion, get_vitality


def get_turn_from_narrator(g: Game) -> Turn:
    try:
        narrator = g.client.messages.parse(
            model=NARRATOR_MODEL,
            max_tokens=NARRATOR_MAX_TOKENS,
            system=NARRATOR_SYSTEM_PROMPT,
            messages=_build_narrator_message(g),
            output_format=Turn,
        )
    except Exception as e:
        raise NarrationError(f"call to narrator failed: {e}") from e

    if narrator.parsed_output is None:
        raise NarrationError("narrator returned None")

    return narrator.parsed_output


def _build_narrator_message(g: Game) -> list[MessageParam]:
    messages = list(g.messages)
    if messages and messages[-1]["role"] == "user":
        content = messages[-1]["content"]
        if not isinstance(content, str):
            return messages

        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": _get_narrator_header(g)},
                {"type": "text", "text": content},
            ],
        }

    return messages


def _get_narrator_header(g: Game) -> str:
    return dedent(f"""
                    NARRATIVE DIRECTION:
                    tension: {g.story_state_log[-1].tension.cue}
                    pace: {g.story_state_log[-1].pace.cue}
                    danger: {g.story_state_log[-1].danger.cue}
                    mood: {g.story_state_log[-1].mood.cue}
                    player vitality: {get_vitality(g.player_stats.health).cue}
                    player exhaustion: {get_exhaustion(g.player_stats.stamina).cue}
                    ------------------------------------
                  """)


def direct_story(g: Game) -> None:
    try:
        director = g.client.messages.parse(
            model=DIRECTOR_MODEL,
            max_tokens=DIRECTOR_MAX_TOKENS,
            system=DIRECTOR_SYSTEM_PROMPT,
            messages=_build_director_message(g),
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
            pace: {story_state.pace}
            player health: {g.player_stats.health}
            player stamina: {g.player_stats.stamina}\n
        """)
    )

    return


def _build_director_message(g: Game) -> list[MessageParam]:
    messages = list(g.messages)
    if messages and messages[-1]["role"] == "user":
        content = messages[-1]["content"]
        if not isinstance(content, str):
            return messages

        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": _get_director_header(g)},
                {"type": "text", "text": content},
            ],
        }

    return messages


def _get_director_header(g: Game) -> str:
    return dedent(f"""
                    PREVIOUS DIRECTION:
                    tension: {g.story_state_log[-1].tension}
                    pace: {g.story_state_log[-1].pace}
                    danger: {g.story_state_log[-1].danger}
                    mood: {g.story_state_log[-1].mood}
                    player_vitality: {get_vitality(g.player_stats.health).cue}
                    player exhaustion: {get_exhaustion(g.player_stats.stamina).cue}
                    ------------------------------------
                  """)


def run_loremaster(g: Game) -> None:
    try:
        director = g.client.messages.parse(
            model=LOREMASTER_MODEL,
            max_tokens=LOREMASTER_MAX_TOKENS,
            system=LOREMASTER_SYSTEM_PROMPT,
            messages=_build_loremaster_message(g),
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
            pace: {story_state.pace}
            player health: {g.player_stats.health}
            player stamina: {g.player_stats.stamina}\n
        """)
    )

    return


def _build_loremaster_message(g: Game) -> list[MessageParam]:
    messages = list(g.messages)
    if messages and messages[-1]["role"] == "user":
        content = messages[-1]["content"]
        if not isinstance(content, str):
            return messages

        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": _get_loremaster_header(g)},
                {"type": "text", "text": content},
            ],
        }

    return messages


def _get_loremaster_header(g: Game) -> str:
    return dedent(f"""
                    PREVIOUS DIRECTION:
                    tension: {g.story_state_log[-1].tension}
                    pace: {g.story_state_log[-1].pace}
                    danger: {g.story_state_log[-1].danger}
                    mood: {g.story_state_log[-1].mood}
                    player_vitality: {get_vitality(g.player_stats.health).cue}
                    player exhaustion: {get_exhaustion(g.player_stats.stamina).cue}
                    ------------------------------------
                  """)
