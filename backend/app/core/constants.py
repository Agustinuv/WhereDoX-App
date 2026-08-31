"""Domain tuning knobs.

Only values someone might reasonably want to argue about or change live here: the rules
of the product, not incidental numbers. Anything environment-specific belongs in
app.core.config instead, because it varies per deployment rather than per decision.
"""

# How many dates a host may have on the table for one event, in total and not per request.
# More than a handful stops being a poll and starts being a calendar.
MAX_PROPOSED_DATES = 5

# A "maybe" is half a "yes" in the tally: enough to break a tie between two slots, never
# enough to outweigh someone who actually committed.
MAYBE_WEIGHT = 0.5

# Ratings are 1-5.
MIN_RATING = 1
MAX_RATING = 5

# Recommender: how much the group's taste counts against how fresh the game is.
# They must add up to 1 so the final score stays in 0-1 and remains comparable.
TASTE_WEIGHT = 0.6
NOVELTY_WEIGHT = 0.4

# What an unrated game is assumed to be worth — the middle of the scale, so a game nobody
# has rated is neither rewarded nor punished for it.
NEUTRAL_RATING = 3.0
