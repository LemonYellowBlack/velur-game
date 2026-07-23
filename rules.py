from domain import Game, Turn, Effect, Exhaustion, Vitality


def handle_turn_effects(g: Game, t: Turn) -> None:
    match t.player_effects.health:
        case Effect.SEVERE:
            g.player_stats.health -= 20
        case Effect.MODERATE:
            g.player_stats.health -= 10
        case Effect.MINOR:
            g.player_stats.health -= 5
        case _:
            pass

    if g.player_stats.health <= 0:
        return

    match t.player_effects.stamina:
        case Effect.SEVERE:
            g.player_stats.stamina -= 20
        case Effect.MODERATE:
            g.player_stats.stamina -= 10
        case Effect.MINOR:
            g.player_stats.stamina -= 5
        case _:
            pass

    if g.player_stats.stamina < 0:
        g.player_stats.stamina = 0


def get_exhaustion(stamina: int) -> Exhaustion:
    if stamina <= 0:
        return Exhaustion.SPENT
    elif stamina <= 25:
        return Exhaustion.FLAGGING
    elif stamina <= 50:
        return Exhaustion.TIRED
    elif stamina <= 75:
        return Exhaustion.WINDED
    else:
        return Exhaustion.FRESH


def get_vitality(health: int) -> Vitality:
    if health <= 30:
        return Vitality.CRITICAL
    elif health <= 50:
        return Vitality.WOUNDED
    elif health <= 70:
        return Vitality.HURT
    elif health <= 90:
        return Vitality.GRAZED
    else:
        return Vitality.WHOLE
