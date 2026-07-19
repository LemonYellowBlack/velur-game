from dotenv import load_dotenv
from pydantic import BaseModel
from dataclasses import dataclass
import anthropic
from anthropic.types import MessageParam

MODEL = "claude-haiku-4-5"
SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
MAX_TOKENS = 1024


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


@dataclass
class Game:
    client: anthropic.Anthropic
    messages: list[MessageParam]
    turn: GameTurn | None = None
    error: str | None = None
    state: str = "playing"


def main() -> None:

    load_dotenv()

    g = Game(
        client=anthropic.Anthropic(),
        messages=[
            {
                "role": "user",
                "content": "Begin a new advendture with a castle scene.",
            },
        ],
    )

    while g.state == "playing":
        g = handle_player_turn(g)
        if g.error is not None:
            raise RuntimeError(g.error)


def handle_player_turn(g: Game) -> Game:
    response = g.client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=g.messages,
        output_format=GameTurn,
    )

    turn = response.parsed_output

    if turn is None:
        g.error = "turn not returned"
        return g

    print("""
    --------------------
        GM TURN
    --------------------
        """)
    print(f"\n{turn.narrative}\n")

    for i, choice in enumerate(turn.choices):
        print(f"\n[#{i + 1}] {choice}")

    print("""
    ---------------------
        PLAYER TURN
    ---------------------
        """)

    raw = input("\n number or q to quit: ")
    if raw == "q":
        g.state = "quit"

    if not raw.isdigit():
        print("please enter a number")
        return g

    index = int(raw) - 1
    if index < 0 or index >= len(turn.choices):
        print("that's not one of the choices")
        return g
    choice = turn.choices[index]

    g.messages.append({"role": "assistant", "content": response.content})
    g.messages.append({"role": "user", "content": f"I choose: {choice}"})

    return g


if __name__ == "__main__":
    main()
