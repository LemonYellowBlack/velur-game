# Premise
- text-based adventure game with ai-generated interactions and images - an AI Game Master.
- lore, plot-points, and characters are prewritten and referenced by the model each turn
- game-state must be passed to model each turn, along with player decisions
- model returns a narrative block, choices for the player to advance the story, and an image that shows the environment (maybe not every turn - just enough to show the environment and whatever character or thing the player is interacting with)
- model will need gaurd-rails that keep responses making sense with the world and driving the story forward 
