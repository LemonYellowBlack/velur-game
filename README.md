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

