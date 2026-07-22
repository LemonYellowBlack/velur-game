from dotenv import load_dotenv
from pydantic import BaseModel, TypeAdapter, Field
from dataclasses import dataclass, asdict, field
import anthropic
from anthropic.types import MessageParam
from enum import Enum, StrEnum
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


class AppState(Enum):
    PLAYING = "playing"
    QUIT = "quit"
    ERROR = "error"
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


class GameTurn(BaseModel):
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
    app_state: AppState = AppState.MENU
    player_stats: PlayerStats = field(default_factory=PlayerStats)
    story_state_log: list[StoryState] = field(default_factory=lambda: [StoryState()])
    messages: list[MessageParam] = field(default_factory=list)
    turn: GameTurn | None = None
    error: str | None = None
    save_file: Path | None = None


def main() -> None:

    _ = load_dotenv()
    g = Game(client=anthropic.Anthropic())

    while g.app_state is not AppState.ERROR and g.app_state is not AppState.QUIT:
        match g.app_state:
            case AppState.PLAYING:
                handle_player_turn(g)
            case AppState.MENU:
                handle_menu(g)

    if g.app_state is AppState.ERROR:
        handle_game_error(g)

    if g.app_state is AppState.QUIT:
        handle_quit()


def handle_menu(g: Game) -> None:
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
            g.app_state = AppState.PLAYING
        case 2:
            save_game(g)
        case 3:
            load_game(g)
        case 4:
            g.app_state = AppState.QUIT
        case _:
            pass


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


def handle_player_turn(g: Game) -> None:
    narrator = g.client.messages.parse(
        model=NARRATOR_MODEL,
        max_tokens=MAX_TOKENS,
        system=NARRATOR_SYSTEM_PROMPT,
        messages=build_turn_message(g),
        output_format=GameTurn,
    )

    g.turn = narrator.parsed_output

    if g.turn is None:
        g.error = "turn not returned"
        return

    handle_player_effects(g, g.player_stats, g.turn.player_effects)

    print(
        dedent("""
            --------------------
                GM TURN
            --------------------\n
        """)
    )
    print(f"{g.turn.narrative}\n")

    for i, choice in enumerate(g.turn.choices):
        print(f"[#{i + 1}] {choice}\n")

    print(
        dedent("""
            ---------------------
                PLAYER TURN
            ---------------------\n
        """)
    )

    raw = input("number or m for menu: ")
    if raw == "m":
        g.app_state = AppState.MENU
        return

    if not raw.isdigit():
        print("please enter a number")
        return

    index = int(raw) - 1
    if index < 0 or index >= len(g.turn.choices):
        print("that's not one of the choices")
        return
    choice = g.turn.choices[index]

    g.messages.append({"role": "assistant", "content": g.turn.model_dump_json()})
    g.messages.append({"role": "user", "content": f"I choose: {choice}"})

    handle_director(g)

    return


def handle_director(g: Game) -> None:
    director = g.client.messages.parse(
        model=DIRECTOR_MODEL,
        max_tokens=MAX_TOKENS,
        system=DIRECTOR_SYSTEM_PROMPT,
        messages=build_director_message(g),
        output_format=StoryState,
    )
    story_state = director.parsed_output

    if story_state is None:
        print("\nNO STORY STATE RETURNED")
        return

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


def handle_player_effects(g: Game, stats: PlayerStats, effects: PlayerEffects) -> None:
    match effects.health:
        case Effect.SEVERE:
            stats.health -= 20
        case Effect.MODERATE:
            stats.health -= 10
        case Effect.MINOR:
            stats.health -= 5
        case _:
            pass

    if stats.health <= 0:
        handle_player_death(g)

    match effects.stamina:
        case Effect.SEVERE:
            stats.stamina -= 20
        case Effect.MODERATE:
            stats.stamina -= 10
        case Effect.MINOR:
            stats.stamina -= 5
        case _:
            pass

    if stats.stamina < 0:
        stats.stamina = 0


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


def handle_player_death(g: Game) -> None:
    print("YOU DIED")
    g.app_state = AppState.QUIT


def handle_game_error(g: Game) -> None:
    raise RuntimeError(g.error)


def handle_quit() -> None:
    print("goodbye.")
    return


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
