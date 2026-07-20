from dotenv import load_dotenv
from pydantic import BaseModel
from dataclasses import dataclass
import anthropic
from anthropic.types import MessageParam
from enum import StrEnum
import json
from pathlib import Path
from textwrap import dedent

MODEL = "claude-haiku-4-5"
SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
FIRST_TURN = "Begin a new adventure with a castle scene."
MAX_TOKENS = 1024
SAVES_DIR = Path(__file__).parent / "saves"


@dataclass
class Game:
    client: anthropic.Anthropic
    state: GameState
    messages: list[MessageParam]
    turn: GameTurn | None = None
    error: str | None = None
    save_file: Path | None = None


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


class GameState(StrEnum):
    PLAYING = "playing"
    QUIT = "quit"
    ERROR = "error"
    MENU = "menu"


def main() -> None:

    _ = load_dotenv()
    g: Game = init_game()

    while g.state is not GameState.ERROR and g.state is not GameState.QUIT:
        while g.state is GameState.PLAYING:
            handle_player_turn(g)
        while g.state is GameState.MENU:
            handle_menu(g)

    if g.state is GameState.ERROR:
        handle_game_error(g)

    if g.state is GameState.QUIT:
        handle_quit()


def init_game() -> Game:
    return Game(client=anthropic.Anthropic(), state=GameState.MENU, messages=[])


def handle_menu(g: Game) -> None:
    opt = input(
        dedent("""
        [#1] play
        [#2] save
        [#3] load
        [#4] quit
    """)
    )

    match int(opt):
        case 1:
            if len(g.messages) == 0:
                g.messages.append({"role": "user", "content": f"{FIRST_TURN}"})
            g.state = GameState.PLAYING
        case 2:
            save_game(g)
        case 3:
            load_game(g)
        case 4:
            g.state = GameState.QUIT
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
        --------------------
    """)
    )
    print(f"\n{g.turn.narrative}\n")

    for i, choice in enumerate(g.turn.choices):
        print(f"\n[#{i + 1}] {choice}")

    print(
        dedent("""
        ---------------------
            PLAYER TURN
        ---------------------
    """)
    )

    raw = input("\n number or m for menu: ")
    if raw == "m":
        g.state = GameState.MENU

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
    print("saving progress...")

    if g.save_file is None:
        g.save_file = SAVES_DIR / "save.json"

    SAVES_DIR.mkdir(parents=True, exist_ok=True)

    d = {"messages": g.messages}
    with g.save_file.open("w") as f:
        json.dump(d, f, indent=2)

    print("progress saved.")
    return


def load_game(g: Game) -> None:
    if not SAVES_DIR.exists():
        print("nothing to load")
        return

    save_files = list(SAVES_DIR.glob("*.json"))
    for i, sfile in enumerate(save_files):
        print(f"\n[#{i + 1}] {sfile}")

    raw = input("\nselect file: ")
    index = int(raw) - 1

    print(f"loading {save_files[index]}")

    with save_files[index].open("r") as f:
        d = json.load(f)
        g.messages = d["messages"]

    print("game loaded")
    g.state = GameState.PLAYING

    return


if __name__ == "__main__":
    main()
