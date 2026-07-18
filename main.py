from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic
from anthropic.types import MessageParam


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


load_dotenv()

client = anthropic.Anthropic()

messages: list[MessageParam] = [
    {
        "role": "user",
        "content": "You are a game master. Begin a new adventure with a castle scene.",
    },
]

while True:
    response = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=messages,
        output_format=GameTurn,
    )

    turn = response.parsed_output

    if turn is None:
        raise RuntimeError("turn not returned")

    print("""

          GM TURN
          --------

          """)
    print(f"\n{turn.narrative}\n")

    for i, choice in enumerate(turn.choices):
        print(f"\n[#{i + 1}] {choice}")

    print("""

        PLAYER TURN
        ---------

          """)

    raw = input("\n number or q to quit: ")
    if raw == "q":
        break

    index = int(raw) - 1
    choice = turn.choices[index]

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": f"I choose: {choice}"})
