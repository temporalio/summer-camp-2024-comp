from random import randint
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel
from temporalio import activity

GENERATE_BOARD_TASK = "generate_board"
SELECT_ATTACK_TASK = "select_attack"
CHECK_ATTACK_TASK = "check_attack"

PLAYER_TASKS_QUEUE = "player-activities-task"


class Coordinates(BaseModel):
    x: int
    y: int

    def __str__(self):
        return f"{self.x}-{self.y}"


class BoardInput(BaseModel):
    size: int
    pieces: List[str]


class BoardOutput(BaseModel):
    size: int
    placement: Dict[str, str]


def next_coordinates(min: int = 0, max: int = 200) -> Coordinates:
    return Coordinates(x=randint(min, max), y=randint(min, max))


@activity.defn(name=GENERATE_BOARD_TASK)
async def generate_board(board_input: BoardInput) -> BoardOutput:
    activity.logger.info(
        f"Generating board with size {board_input.size}x{board_input.size}"
    )

    places = {}
    for piece in board_input.pieces:
        placed = False
        while not placed:
            coordinates = next_coordinates(max=board_input.size)
            if str(coordinates) in places:
                continue
            else:
                places[str(coordinates)] = piece
                placed = True

    activity.logger.info(
        f"Got board with size {board_input.size}x{board_input.size}: {places}"
    )
    return BoardOutput(
        size=board_input.size,
        placement=places,
    )


@activity.defn(name=SELECT_ATTACK_TASK)
async def select_attack(
    previous_plays: List[Coordinates], board: BoardOutput
) -> Coordinates:
    activity.logger.info("Selecting attack")

    i = 1
    while True:
        attack = next_coordinates(max=board.size)
        for previous in previous_plays:
            if attack == previous:
                break
        else:
            activity.logger.info(f"Found attack after {i} attempts: {attack}")
            return attack
        i += 1


@activity.defn(name=CHECK_ATTACK_TASK)
async def check_attack(attack: Coordinates, board: BoardOutput) -> Optional[str]:
    activity.logger.info(f"Checking attack: {attack}")

    hit = board.placement.get(str(attack))
    if hit:
        activity.logger.info(f"Attack hit a piece: {hit}")
        return hit

    activity.logger.info("Attack failed")
    return None


PLAYER_TASKS = [generate_board, select_attack, check_attack]
