from dotenv import load_dotenv
from pydantic import BaseModel, TypeAdapter
from dataclasses import dataclass, asdict
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


class Amount(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Speed(StrEnum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


@dataclass
class Player:
    health: int
    stamina: int


class StoryState(BaseModel):
    tension: Amount
    pace: Speed


@dataclass
class Game:
    client: anthropic.Anthropic
    app_state: AppState
    player: Player
    story_state_log: list[StoryState]
    messages: list[MessageParam]
    turn: GameTurn | None = None
    error: str | None = None
    save_file: Path | None = None


def main() -> None:

    _ = load_dotenv()
    g: Game = init_game()

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


def init_game() -> Game:
    player = Player(health=100, stamina=100)
    story_state = StoryState(tension=Amount.LOW, pace=Speed.SLOW)
    log = [story_state]
    return Game(
        client=anthropic.Anthropic(),
        app_state=AppState.MENU,
        player=player,
        story_state_log=log,
        messages=[],
    )


def handle_menu(g: Game) -> None:
    file_name = ""
    if g.save_file is not None:
        file_name = g.save_file.name

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

    match int(opt):
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
        print(f"\n[#{i + 1}] {s}")

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
    else:
        file_name = saves[index]

    print(f"saving to {file_name}...")
    g.save_file = SAVES_DIR / f"{file_name}"

    d = {
        "messages": g.messages,
        "story_state_log": [s.model_dump(mode="json") for s in g.story_state_log],
        "player": asdict(g.player),
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
        print(f"\n[#{i + 1}] {sfile}")

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
    print(f"loading {game_file}")

    with game_file.open("r") as f:
        d = json.load(f)
        g.messages = d["messages"]
        g.story_state_log = [StoryState.model_validate(x) for x in d["story_state_log"]]
        g.player = TypeAdapter(Player).validate_python(d["player"])

    g.save_file = game_file
    print(f"{g.save_file} loaded")

    return


if __name__ == "__main__":
    main()
