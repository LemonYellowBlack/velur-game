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

MODEL = "claude-haiku-4-5"
SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
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


class Pace(StrEnum):
    LULL = "lull"
    STEADY = "steady"
    RISING = "rising"
    BREAKNECK = "breakneck"


class Exhaustion(StrEnum):
    FRESH = "fresh"
    WINDED = "winded"
    TIRED = "tired"
    FLAGGING = "flagging"
    SPENT = "spent"


class Danger(StrEnum):
    SAFE = "safe"
    RISKY = "risky"
    PERILOUS = "perilous"
    DEADLY = "deadly"


class Mood(StrEnum):
    HOPEFULL = "hopefull"
    SOMBER = "somber"
    OMINOUS = "ominous"
    BLEAK = "bleak"


class PlayerState(BaseModel):
    exhaustion: Exhaustion = Exhaustion.FRESH


class StoryState(BaseModel):
    tension: Tension = Tension.UNEASY
    pace: Pace = Pace.STEADY
    danger: Danger = Danger.RISKY
    mood: Mood = Mood.OMINOUS


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
    player_state: PlayerState = field(default_factory=PlayerState)
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
                    tension: {g.story_state_log[-1].tension}
                    pace: {g.story_state_log[-1].pace}
                    danger: {g.story_state_log[-1].danger}
                    mood: {g.story_state_log[-1].mood}
                    player's exhaustion: {g.player_state.exhaustion}
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


def handle_player_turn(g: Game) -> None:
    response = g.client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=build_turn_message(g),
        output_format=GameTurn,
    )

    g.turn = response.parsed_output

    if g.turn is None:
        g.error = "turn not returned"
        return

    handle_player_effects(g, g.player_stats, g.player_state, g.turn.player_effects)

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

    return


def handle_player_effects(
    g: Game, stats: PlayerStats, state: PlayerState, effects: PlayerEffects
) -> None:
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

    if stats.stamina <= 0:
        stats.stamina = 0
        state.exhaustion = Exhaustion.SPENT
    elif stats.stamina <= 25:
        state.exhaustion = Exhaustion.FLAGGING
    elif stats.stamina <= 50:
        state.exhaustion = Exhaustion.TIRED
    elif stats.stamina <= 75:
        state.exhaustion = Exhaustion.WINDED
    else:
        state.exhaustion = Exhaustion.FRESH


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
        "player_state": g.player_state.model_dump(mode="json"),
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
        g.player_state = PlayerState.model_validate(d["player_state"])
        g.player_stats = TypeAdapter(PlayerStats).validate_python(d["player_stats"])

    g.save_file = game_file
    print(f"{g.save_file.stem} loaded")

    return


if __name__ == "__main__":
    main()
