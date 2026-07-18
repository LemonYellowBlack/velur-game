from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic
from anthropic.types import MessageParam

MODEL = "claude-haiku-4-5"
SYSTEM_PROMPT = "You are the Game Master of a dark fantasy adventure."
MAX_TOKENS = 1024


class GameTurn(BaseModel):
    narrative: str
    choices: list[str]


def main() -> None:

    load_dotenv()

    client = anthropic.Anthropic()
    messages: list[MessageParam] = [
        {
            "role": "user",
            "content": "Begin a new adventure with a castle scene.",
        },
    ]

    while True:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_format=GameTurn,
        )

        turn = response.parsed_output

        if turn is None:
            raise RuntimeError("turn not returned")

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
            break

        if not raw.isdigit():
            print("please enter a number")
            continue

        index = int(raw) - 1
        if index < 0 or index >= len(turn.choices):
            print("that's not one of the choices")
            continue
        choice = turn.choices[index]

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": f"I choose: {choice}"})


if __name__ == "__main__":
    main()
