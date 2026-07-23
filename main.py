from dotenv import load_dotenv
from pydantic import BaseModel, TypeAdapter, Field
from dataclasses import dataclass, asdict, field
import anthropic
from anthropic.types import MessageParam
from enum import StrEnum
import json
from pathlib import Path
from textwrap import dedent
from datetime import datetime

NARRATOR_MODEL = "claude-haiku-4-5"
NARRATOR_SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
DIRECTOR_MODEL = "claude-sonnet-4-6"
DIRECTOR_SYSTEM_PROMPT = dedent("""
    You are the Director of a dark fantasy adventure, responsible for shaping the story's arc over time.
    Read the story and set tension, pace, danger, and mood for the next beat.
    A story must breathe: build tension toward peaks and release afterward. 
    Escalate or lower stakes to keep the story moving.
    """)
FIRST_TURN = "Begin a new adventure with a castle scene."
MAX_TOKENS = 1024
SAVES_DIR = Path(__file__).parent / "saves"


class AppState(StrEnum):
    PLAYING = "playing"
    QUIT = "quit"
    MENU = "menu"


class Effect(StrEnum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class Tension(StrEnum):
    CALM = "calm"
    UNEASY = "uneasy"
    TENSE = "tense"
    DREAD = "dread"
    TERROR = "terror"

    @property
    def cue(self) -> str:
        return {
            Tension.CALM: "at ease; nothing presses on the mind",
            Tension.UNEASY: "something feels off; a prickle of doubt",
            Tension.TENSE: "nerves drawn tight; poised for something",
            Tension.DREAD: "a heavy certainty that something is wrong",
            Tension.TERROR: "gripping fear; the mind screams to flee",
        }[self]


class Pace(StrEnum):
    LULL = "lull"
    MEASURED = "measured"
    BRISK = "brisk"
    BREAKNECK = "breakneck"

    @property
    def cue(self) -> str:
        return {
            Pace.LULL: "time to linger; nothing hurries the moment",
            Pace.MEASURED: "events move at a steady, even step",
            Pace.BRISK: "things move quickly; little time to dwell",
            Pace.BREAKNECK: "relentless; no moment to breathe",
        }[self]


class Danger(StrEnum):
    SAFE = "safe"
    RISKY = "risky"
    PERILOUS = "perilous"
    DEADLY = "deadly"

    @property
    def cue(self) -> str:
        return {
            Danger.SAFE: "no real threat to body or life",
            Danger.RISKY: "harm is possible if careless",
            Danger.PERILOUS: "serious injury likely without care",
            Danger.DEADLY: "death is a real and present outcome",
        }[self]


class Mood(StrEnum):
    WONDROUS = "wondrous"
    HOPEFUL = "hopeful"
    MELANCHOLY = "melancholy"
    EERIE = "eerie"
    BLEAK = "bleak"

    @property
    def cue(self) -> str:
        return {
            Mood.WONDROUS: "awe and beauty; the world astonishes",
            Mood.HOPEFUL: "warmth and promise; things may yet turn out",
            Mood.MELANCHOLY: "quiet sorrow; beauty tinged with loss",
            Mood.EERIE: "unnatural stillness; something is not right",
            Mood.BLEAK: "cold and hopeless; comfort is absent",
        }[self]


class Exhaustion(StrEnum):
    FRESH = "fresh"
    WINDED = "winded"
    TIRED = "tired"
    FLAGGING = "flagging"
    SPENT = "spent"

    @property
    def cue(self) -> str:
        return {
            Exhaustion.FRESH: "unwearied; moves freely",
            Exhaustion.WINDED: "breathing hard; brief effort tells",
            Exhaustion.TIRED: "tiring; sustained effort is a strain",
            Exhaustion.FLAGGING: "near their limit; failing at hard exertion",
            Exhaustion.SPENT: "utterly spent; can barely stand",
        }[self]


class StoryState(BaseModel):
    tension: Tension = Field(
        default=Tension.UNEASY,
        description=(
            "the felt emotional pressure of the scene, "
            "independent of actual physical threat; "
            "raise and lower as the narrative's stakes change."
        ),
    )
    pace: Pace = Field(
        default=Pace.MEASURED,
        description=(
            "how fast events are unfolding: "
            "raise during action or rapid consequenses; "
            "lower during exploration, dialogue, or reflection - when the player can take their time"
        ),
    )
    danger: Danger = Field(
        default=Danger.RISKY,
        description=(
            "the objective threat to the player - "
            "can be independent from the player's perception in the event of an unknown danger"
        ),
    )
    mood: Mood = Field(
        default=Mood.MELANCHOLY,
        description=("the asthetic tone or atmosphere of the current setting"),
    )
    rationale: str = "initial state"


class PlayerEffects(BaseModel):
    health: Effect = Field(
        default=Effect.NONE,
        description=(
            "indicates how much the player's health changed this turn "
            "based on injury or harm in the narrative"
        ),
    )
    stamina: Effect = Field(
        default=Effect.NONE,
        description=(
            "indicates much the player's stamina was drained this turn "
            "based on exertion in the narrative"
        ),
    )


class Turn(BaseModel):
    narrative: str
    choices: list[str]
    player_effects: PlayerEffects


@dataclass
class PlayerStats:
    health: int = 100
    stamina: int = 100


@dataclass
class Game:
    client: anthropic.Anthropic
    player_stats: PlayerStats = field(default_factory=PlayerStats)
    story_state_log: list[StoryState] = field(default_factory=lambda: [StoryState()])
    messages: list[MessageParam] = field(default_factory=list)
    save_file: Path | None = None


class GameError(Exception):
    """any failure the game deliberately anticipates"""


class NarrationError(GameError):
    """the player's turn cannot be produced"""


class DirectionError(GameError):
    """story-state has not been changed"""


def main() -> None:
    _ = load_dotenv()
    g = Game(client=anthropic.Anthropic())

    state = AppState.MENU
    while state is not AppState.QUIT:
        match state:
            case AppState.MENU:
                state = menu(g)
            case AppState.PLAYING:
                state = play(g)

    assert state is AppState.QUIT
    print("goodbye.")


def menu(g: Game) -> AppState:
    file_name = ""
    if g.save_file is not None:
        file_name = g.save_file.name

    option = None
    while option is None:
        opt = input(
            dedent(f"""
            MAIN MENU
            -----------------
            [#1] play {file_name}
            [#2] save
            [#3] load
            [#4] quit\n
        """)
        )

        if opt.isdigit():
            option = int(opt)
        else:
            print("must be a number")

    match option:
        case 1:
            if len(g.messages) == 0:
                g.messages.append({"role": "user", "content": FIRST_TURN})
            return AppState.PLAYING
        case 2:
            save_game(g)
        case 3:
            load_game(g)
        case 4:
            return AppState.QUIT
        case _:
            pass

    return AppState.MENU


def play(g: Game) -> AppState:
    try:
        t = get_turn_from_narrator(g)
    except NarrationError as e:
        print(f"NARRATION FAILURE: {e}")
        return AppState.MENU

    if handle_user_choice(g, t) is AppState.MENU:
        return AppState.MENU

    handle_turn_effects(g, t)
    if g.player_stats.health <= 0:
        print("YOU DIED")
        return AppState.QUIT

    try:
        direct_story(g)
    except DirectionError as e:
        print(f"DIRECTOR ERROR: {e}")

    return AppState.PLAYING


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


def handle_user_choice(g: Game, t: Turn) -> AppState:
    print(
        dedent(f"""
            --------------------
                GM TURN
            --------------------

            {t.narrative}\n
        """)
    )

    options = t.choices + [AppState.MENU]
    for i, choice in enumerate(options):
        print(f"[#{i + 1}] {choice}\n")

    print(
        dedent("""
            ---------------------
                PLAYER TURN
            ---------------------\n
        """)
    )

    choice: str | None = None
    while choice is None:
        raw = input("select an option: ")

        if not raw.isdigit():
            print("please enter a number")
            continue

        index = int(raw) - 1
        if index < 0 or index >= len(options):
            print("that's not one of the choices")
            continue

        choice = options[index]

    if choice == AppState.MENU:
        return AppState.MENU

    g.messages.append({"role": "assistant", "content": t.model_dump_json()})
    g.messages.append({"role": "user", "content": f"I choose: {choice}"})

    return AppState.PLAYING


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


def handle_turn_effects(g: Game, t: Turn) -> None:
    match t.player_effects.health:
        case Effect.SEVERE:
            g.player_stats.health -= 20
        case Effect.MODERATE:
            g.player_stats.health -= 10
        case Effect.MINOR:
            g.player_stats.health -= 5
        case _:
            pass

    if g.player_stats.health <= 0:
        return

    match t.player_effects.stamina:
        case Effect.SEVERE:
            g.player_stats.stamina -= 20
        case Effect.MODERATE:
            g.player_stats.stamina -= 10
        case Effect.MINOR:
            g.player_stats.stamina -= 5
        case _:
            pass

    if g.player_stats.stamina < 0:
        g.player_stats.stamina = 0


def get_exhaustion(stamina: int) -> Exhaustion:
    if stamina <= 0:
        return Exhaustion.SPENT
    elif stamina <= 25:
        return Exhaustion.FLAGGING
    elif stamina <= 50:
        return Exhaustion.TIRED
    elif stamina <= 75:
        return Exhaustion.WINDED
    else:
        return Exhaustion.FRESH


def save_game(g: Game) -> None:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)

    saves = [p.name for p in SAVES_DIR.glob("*.json")]
    saves.insert(0, "new save")

    for i, s in enumerate(saves):
        print(f"\n[#{i + 1}] {Path(s).stem}")

    index = None
    while index is None:
        raw = input("\nselect file: ")

        if not raw.isdigit():
            print("must be a number")
            continue

        _index = int(raw) - 1

        if _index < 0 or _index >= len(saves):
            print("must be an option")
            continue

        index = _index

    file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    if index == 0:
        file_name = input("file name: ")
        if not file_name.endswith(".json"):
            file_name += ".json"
    else:
        file_name = saves[index]

    print(f"saving to {file_name}...")
    g.save_file = SAVES_DIR / f"{file_name}"

    d = {
        "messages": g.messages,
        "story_state_log": [s.model_dump(mode="json") for s in g.story_state_log],
        "player_stats": asdict(g.player_stats),
    }
    with g.save_file.open("w") as f:
        json.dump(d, f, indent=2)

    print("progress saved.")
    return


def load_game(g: Game) -> None:
    if not SAVES_DIR.exists():
        print("no saves directory")
        return

    saves = list(SAVES_DIR.glob("*.json"))
    if len(saves) == 0:
        print("no saves files")
        return

    for i, sfile in enumerate(saves):
        print(f"\n[#{i + 1}] {sfile.stem}")

    index = None
    while index is None:
        raw = input("\nselect file: ")

        if not raw.isdigit():
            print("must be a number")
            continue

        _index = int(raw) - 1

        if _index < 0 or _index >= len(saves):
            print("must be an option")
            continue

        index = _index

    game_file = saves[index]
    print(f"loading {game_file.stem}")

    with game_file.open("r") as f:
        d = json.load(f)
        g.messages = d["messages"]
        g.story_state_log = [StoryState.model_validate(x) for x in d["story_state_log"]]
        g.player_stats = TypeAdapter(PlayerStats).validate_python(d["player_stats"])

    g.save_file = game_file
    print(f"{g.save_file.stem} loaded")

    return


if __name__ == "__main__":
    main()
