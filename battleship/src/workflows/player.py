import string
from datetime import timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.activities.player import (PLAYER_TASKS_QUEUE, BoardInput,
                                       BoardOutput, Coordinates, check_attack,
                                       generate_board, select_attack)

alphabet = list(string.ascii_uppercase)


class PlayerStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    ATTACKING = "attacking"
    UNDER_ATTACK = "under_attack"
    GAME_OVER = "game_over"


class PlayerInput(BaseModel):
    name: str
    competitor_id: str
    initial_status: PlayerStatus


class PlayerOutput(BaseModel):
    collected_letters: List[str]


@workflow.defn
class Player:
    name = "player"
    task_queue = "player-tasks"

    competitor_id = ""
    status: str = PlayerStatus.WAITING

    board: BoardOutput
    previous_attacks: List[Coordinates] = []
    letters_won: List[str] = []

    received_attack: Optional[Coordinates]
    letters_lost: List[str] = []

    is_game_over = False

    @workflow.signal
    def get_turn(self) -> None:
        if self.status != PlayerStatus.WAITING:
            workflow.logger.warning(f"Player was not in 'waiting' state: {self.status}")

        workflow.logger.info(f"Got turn!")
        self.status = PlayerStatus.PLAYING

    @workflow.signal
    def attack(self, attack: Coordinates) -> None:
        if self.status != PlayerStatus.WAITING:
            workflow.logger.warning(f"Player was not in 'waiting' state: {self.status}")

        workflow.logger.info(f"Receiving attack!")
        self.status = PlayerStatus.UNDER_ATTACK
        self.received_attack = attack
        return

    @workflow.signal
    def result(self, hit: Optional[str]) -> None:
        if self.status != PlayerStatus.ATTACKING:
            workflow.logger.warning(
                f"Player was not in 'attacking' state: {self.status}"
            )

        if hit and hit not in self.letters_won:
            self.letters_won.append(hit)
            workflow.logger.info(
                f"Hit letter {hit}! Already have {len(self.letters_won)} hits."
            )

        self.status = PlayerStatus.WAITING
        workflow.logger.info(f"Waiting for next turn!")
        return

    @workflow.signal
    def game_over(self) -> None:
        workflow.logger.info("Lost game!")
        self.status = PlayerStatus.GAME_OVER
        self.is_game_over = True
        return

    @workflow.run
    async def run(self, input: PlayerInput) -> PlayerOutput:
        self.status = input.initial_status
        self.competitor_id = input.competitor_id
        competitor_handle = workflow.get_external_workflow_handle_for(
            Player.run, self.competitor_id
        )

        # Initial step: Place alphabet letters in board
        # for game
        output = await workflow.execute_activity_method(
            activity=generate_board,
            # TODO: make parameter. Now it's a hack so it's faster
            arg=BoardInput(size=10, pieces=alphabet),
            task_queue=PLAYER_TASKS_QUEUE,
            start_to_close_timeout=timedelta(seconds=1),
        )
        self.board = output

        while not self.is_game_over:
            # Workflow only moves when status changes
            await workflow.wait_condition(lambda: self.status != PlayerStatus.WAITING)

            if self.status == PlayerStatus.PLAYING:
                # Currently this players turn
                output = await workflow.execute_activity_method(
                    activity=select_attack,
                    args=[self.previous_attacks, self.board],
                    task_queue=PLAYER_TASKS_QUEUE,
                    start_to_close_timeout=timedelta(seconds=1),
                )

                self.status = PlayerStatus.ATTACKING
                self.previous_attacks.append(output)
                await competitor_handle.signal(Player.attack, output)

                # Workflow only continues when the result is received
                await workflow.wait_condition(
                    lambda: self.status != PlayerStatus.ATTACKING
                )
                if len(self.letters_won) >= len(alphabet):
                    workflow.logger.info("Won game!")
                    await competitor_handle.signal(Player.game_over)
                    self.status = PlayerStatus.GAME_OVER
                    self.is_game_over = True
                    return PlayerOutput(collected_letters=self.letters_won)
                else:
                    await competitor_handle.signal(Player.get_turn)

            elif self.status == PlayerStatus.UNDER_ATTACK:
                output = await workflow.execute_activity_method(
                    activity=check_attack,
                    args=[self.received_attack, self.board],
                    task_queue=PLAYER_TASKS_QUEUE,
                    start_to_close_timeout=timedelta(seconds=1),
                )
                if output and output not in self.letters_lost:
                    self.letters_lost.append(output)

                await competitor_handle.signal(Player.result, output)

                # Workflow only continues when the result is received
                await workflow.wait_condition(
                    lambda: self.status != PlayerStatus.UNDER_ATTACK
                )
                self.received_attack = None

        return PlayerOutput(collected_letters=self.letters_won)
