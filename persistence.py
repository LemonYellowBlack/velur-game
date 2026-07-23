import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from pydantic import TypeAdapter
from config import SAVES_DIR
from domain import Game, StoryState, PlayerStats


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
