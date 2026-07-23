from textwrap import dedent
from config import FIRST_TURN
from domain import (
    Game,
    AppState,
    Turn,
    NarrationError,
    DirectionError,
    handle_turn_effects,
)
from agents import get_turn_from_narrator, direct_story
from persistence import save_game, load_game


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
