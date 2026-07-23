from enum import StrEnum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import anthropic
from anthropic.types import MessageParam
from pathlib import Path


class AppState(StrEnum):
    PLAYING = "playing"
    QUIT = "quit"
    MENU = "menu"


class Effect(StrEnum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class Tension(StrEnum):
    CALM = "calm"
    UNEASY = "uneasy"
    TENSE = "tense"
    DREAD = "dread"
    TERROR = "terror"

    @property
    def cue(self) -> str:
        return {
            Tension.CALM: "at ease; nothing presses on the mind",
            Tension.UNEASY: "something feels off; a prickle of doubt",
            Tension.TENSE: "nerves drawn tight; poised for something",
            Tension.DREAD: "a heavy certainty that something is wrong",
            Tension.TERROR: "gripping fear; the mind screams to flee",
        }[self]


class Pace(StrEnum):
    LULL = "lull"
    MEASURED = "measured"
    BRISK = "brisk"
    BREAKNECK = "breakneck"

    @property
    def cue(self) -> str:
        return {
            Pace.LULL: "time to linger; nothing hurries the moment",
            Pace.MEASURED: "events move at a steady, even step",
            Pace.BRISK: "things move quickly; little time to dwell",
            Pace.BREAKNECK: "relentless; no moment to breathe",
        }[self]


class Danger(StrEnum):
    SAFE = "safe"
    RISKY = "risky"
    PERILOUS = "perilous"
    DEADLY = "deadly"

    @property
    def cue(self) -> str:
        return {
            Danger.SAFE: "no real threat to body or life",
            Danger.RISKY: "harm is possible if careless",
            Danger.PERILOUS: "serious injury likely without care",
            Danger.DEADLY: "death is a real and present outcome",
        }[self]


class Mood(StrEnum):
    WONDROUS = "wondrous"
    HOPEFUL = "hopeful"
    MELANCHOLY = "melancholy"
    EERIE = "eerie"
    BLEAK = "bleak"

    @property
    def cue(self) -> str:
        return {
            Mood.WONDROUS: "awe and beauty; the world astonishes",
            Mood.HOPEFUL: "warmth and promise; things may yet turn out",
            Mood.MELANCHOLY: "quiet sorrow; beauty tinged with loss",
            Mood.EERIE: "unnatural stillness; something is not right",
            Mood.BLEAK: "cold and hopeless; comfort is absent",
        }[self]


class Exhaustion(StrEnum):
    FRESH = "fresh"
    WINDED = "winded"
    TIRED = "tired"
    FLAGGING = "flagging"
    SPENT = "spent"

    @property
    def cue(self) -> str:
        return {
            Exhaustion.FRESH: "unwearied; moves freely",
            Exhaustion.WINDED: "breathing hard; brief effort tells",
            Exhaustion.TIRED: "tiring; sustained effort is a strain",
            Exhaustion.FLAGGING: "near their limit; failing at hard exertion",
            Exhaustion.SPENT: "utterly spent; can barely stand",
        }[self]


class Vitality(StrEnum):
    WHOLE = "whole"
    GRAZED = "grazed"
    HURT = "hurt"
    WOUNDED = "wounded"
    CRITICAL = "critical"

    @property
    def cue(self) -> str:
        return {
            Vitality.WHOLE: "unhurt; no pain, no restriction",
            Vitality.GRAZED: "minor cuts and bruises; more nuisance than hindrance",
            Vitality.HURT: "wounds ache; movement brings pain",
            Vitality.WOUNDED: "serious injury; the body struggles to keep up",
            Vitality.CRITICAL: "grievously hurt; death is close without aid",
        }[self]


class StoryState(BaseModel):
    tension: Tension = Field(
        default=Tension.UNEASY,
        description=(
            "the felt emotional pressure of the scene, "
            "independent of actual physical threat; "
            "raise and lower as the narrative's stakes change."
        ),
    )
    pace: Pace = Field(
        default=Pace.MEASURED,
        description=(
            "how fast events are unfolding: "
            "raise during action or rapid consequenses; "
            "lower during exploration, dialogue, or reflection - when the player can take their time"
        ),
    )
    danger: Danger = Field(
        default=Danger.RISKY,
        description=(
            "the objective threat to the player - "
            "can be independent from the player's perception in the event of an unknown danger"
        ),
    )
    mood: Mood = Field(
        default=Mood.MELANCHOLY,
        description=("the asthetic tone or atmosphere of the current setting"),
    )
    rationale: str = "initial state"


class PlayerEffects(BaseModel):
    health: Effect = Field(
        default=Effect.NONE,
        description=(
            "indicates how much the player's health changed this turn "
            "based on injury or harm in the narrative"
        ),
    )
    stamina: Effect = Field(
        default=Effect.NONE,
        description=(
            "indicates much the player's stamina was drained this turn "
            "based on exertion in the narrative"
        ),
    )


class Turn(BaseModel):
    narrative: str
    choices: list[str]
    player_effects: PlayerEffects


@dataclass
class PlayerStats:
    health: int = 100
    stamina: int = 100


@dataclass
class Game:
    client: anthropic.Anthropic
    player_stats: PlayerStats = field(default_factory=PlayerStats)
    story_state_log: list[StoryState] = field(default_factory=lambda: [StoryState()])
    messages: list[MessageParam] = field(default_factory=list)
    save_file: Path | None = None


class GameError(Exception):
    """any failure the game deliberately anticipates"""


class NarrationError(GameError):
    """the player's turn cannot be produced"""


class DirectionError(GameError):
    """story-state has not been changed"""
