## Premise
- text-based adventure game with ai-generated interactions and images - an AI Game Master.
- lore, plot-points, and characters are prewritten and referenced by the model each turn
- game-state must be passed to model each turn, along with player decisions
- model returns a narrative block, choices for the player to advance the story, and an image that shows the environment (maybe not every turn - just enough to show the environment and whatever character or thing the player is interacting with)
- model will need gaurd-rails that keep responses making sense with the world and driving the story forward 

## Architecture
- htmx frontend, purposefully small
- python backend for AI libraries and sdks
- postgres with pgvector (40MB of lore: wiki, narrative, maps)
- github workflows for CI
- terraform for IAC
- aws: EC2, S3 (maybe R2), aurora, bedrock
- cloudflare: DNS

## Context Management
- smaller model handles turn-by-turn from a Game Context block
- larger model(s) work in the background asyncronously to adjust Game Context 
- Game Context is influenced by:
    - World State (corpus wiki, facts about the world)
    - Character State (how the player character, and revelvant NPCs have been affected)
    - Story State (plot points, tension, pacing, arcs)

## TODO
- model calls to manage story_state:
    - when should this happen and what is the trigger?
    - does it check corpus (maybe a third tier of model) and how is that loaded?
    - if director agent modifies state async does that cause a noticible issue for the lagging turn?
- consider where/when stamina and exhaustion should be calculated: 
    - will the current placement cause drift or bugs if/when other factors affect either/both?
    - should exhaustion just be derived (`check_exhaustion()`) when needed?
