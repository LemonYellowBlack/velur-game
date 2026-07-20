from dotenv import load_dotenv
from pydantic import BaseModel
from dataclasses import dataclass
import anthropic
from anthropic.types import MessageParam
from enum import Enum
import json
from pathlib import Path
from textwrap import dedent
from datetime import datetime

MODEL = "claude-haiku-4-5"
SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
FIRST_TURN = "Begin a new adventure with a castle scene."
MAX_TOKENS = 1024
SAVES_DIR = Path(__file__).parent / "saves"


@dataclass
class Game:
    client: anthropic.Anthropic
    state: AppState
    messages: list[MessageParam]
    turn: GameTurn | None = None
    error: str | None = None
    save_file: Path | None = None


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


class AppState(Enum):
    PLAYING = "playing"
    QUIT = "quit"
    ERROR = "error"
    MENU = "menu"


def main() -> None:

    _ = load_dotenv()
    g: Game = init_game()

    while g.state is not AppState.ERROR and g.state is not AppState.QUIT:
        match g.state:
            case AppState.PLAYING:
                handle_player_turn(g)
            case AppState.MENU:
                handle_menu(g)

    if g.state is AppState.ERROR:
        handle_game_error(g)

    if g.state is AppState.QUIT:
        handle_quit()


def init_game() -> Game:
    return Game(client=anthropic.Anthropic(), state=AppState.MENU, messages=[])


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
                g.messages.append({"role": "user", "content": f"{FIRST_TURN}"})
            g.state = AppState.PLAYING
        case 2:
            save_game(g)
        case 3:
            load_game(g)
        case 4:
            g.state = AppState.QUIT
        case _:
            pass


def handle_player_turn(g: Game) -> None:
    response = g.client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=g.messages,
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
        g.state = AppState.MENU

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

    d = {"messages": g.messages}
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

    g.save_file = game_file
    print(f"{g.save_file} loaded")

    return


if __name__ == "__main__":
    main()
