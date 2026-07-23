from dotenv import load_dotenv
import anthropic
from domain import Game, AppState
from engine import menu, play


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


if __name__ == "__main__":
    main()
