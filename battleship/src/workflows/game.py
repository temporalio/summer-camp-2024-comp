from datetime import timedelta
from typing import List

from pydantic import BaseModel
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.activities.game import choose_starting_player
    from src.activities.player import PLAYER_TASKS_QUEUE
    from src.workflows.player import Player, PlayerInput, PlayerStatus


class GameOutput(BaseModel):
    winner: str
    collected_letters: List[str]


@workflow.defn
class Game:
    name = "game"
    task_queue = "game-tasks"

    @workflow.run
    async def run(self) -> GameOutput:
        """
        Runs a game workflow, essentially triggering child workflows as separate players that will
         try to collect the letters of the alphabet of the opponent as fast as possible, in a
         battleship fashion.

        The workflow does the following:
         1. selects a starting player
         2. triggers the starts of the 2 players

         Once the players are done, it collects the results and outputs the winner and collected letters,
          in the collected order

        :return:
            GameOutput: the winner and collected letters
        """

        workflow_info = workflow.info()
        player1_id = workflow_info.workflow_id + "player1"
        player2_id = workflow_info.workflow_id + "player2"

        starting_player = await workflow.execute_activity_method(
            activity=choose_starting_player,
            arg=[player1_id, player2_id],
            start_to_close_timeout=timedelta(seconds=1),
            task_queue=PLAYER_TASKS_QUEUE,
        )
        if starting_player == player1_id:
            player1_status = PlayerStatus.PLAYING
            player2_status = PlayerStatus.WAITING
        else:
            player1_status = PlayerStatus.WAITING
            player2_status = PlayerStatus.PLAYING

        workflow.logger.info(
            f"Starting player 1 with id {player1_id} and status {player1_status}"
        )
        player1_handle = await workflow.start_child_workflow(
            Player.run,
            PlayerInput(
                name="player 1", initial_status=player1_status, competitor_id=player2_id
            ),
            task_queue=Player.task_queue,
            id=player1_id,
            parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
        )

        workflow.logger.info(
            f"Starting player 2 with id {player2_id} and status {player2_status}"
        )
        player2_handle = await workflow.start_child_workflow(
            Player.run,
            PlayerInput(
                name="player 2", initial_status=player2_status, competitor_id=player1_id
            ),
            task_queue=Player.task_queue,
            id=player2_id,
            parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
        )

        await workflow.wait_condition(player1_handle.done)
        await workflow.wait_condition(player2_handle.done)

        result_player1 = player1_handle.result()
        result_player2 = player2_handle.result()

        if len(result_player1.collected_letters) > len(
            result_player2.collected_letters
        ):
            workflow.logger.info(f"Game ended with Player 1 as winner")
            return GameOutput(
                winner="Player 1",
                collected_letters=result_player1.collected_letters,
            )
        else:
            workflow.logger.info(f"Game ended with Player 2 as winner")
            return GameOutput(
                winner="Player 2",
                collected_letters=result_player2.collected_letters,
            )
