from random import choice
from typing import List

from temporalio import activity


@activity.defn(name="choose_starting_player")
async def choose_starting_player(players: List[str]) -> str:
    return choice(players)
