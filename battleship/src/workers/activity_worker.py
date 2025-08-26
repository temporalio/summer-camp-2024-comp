import logging

import click
from temporalio.client import Client
from temporalio.worker import Worker

from src import coro, interrupt_event
from src.activities.game import choose_starting_player
from src.activities.player import (PLAYER_TASKS_QUEUE, check_attack,
                                   generate_board, select_attack)
from src.settings import TemporalClusterSettings
from src.utils.pydantic_converter import pydantic_data_converter

activities = {
    # "game": {"tasks": [], "queue": ""},
    "player": {
        "tasks": [generate_board, select_attack, check_attack, choose_starting_player],
        "queue": PLAYER_TASKS_QUEUE,
    },
}


@click.command("activity", context_settings={"show_default": True})
@click.option("-n", "--name", type=click.Choice(activities.keys()), required=True)
@click.option("-v", "--verbose", is_flag=True)
@coro
async def start_activities_worker(name, verbose):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("activies")
    logger.setLevel(level=logging.DEBUG if verbose else logging.INFO)
    logger.debug(f"{verbose=},")

    logger.info("Initializing client...")
    settings = TemporalClusterSettings()
    client = await Client.connect(
        target_host=settings.host,
        namespace=settings.namespace,
        tls=settings.tls_config,
        data_converter=pydantic_data_converter,
    )
    logger.info(f'Client initialized! Connected to "{settings.host}"...')
    activity_tasks = activities.get(name)

    logger.info("Initializing worker...")
    async with Worker(
        client=client,
        task_queue=activity_tasks.get("queue"),
        activities=activity_tasks.get("tasks"),
        debug_mode=verbose,
    ):
        # Wait until interrupted
        logger.info(f"Worker initialized, ctrl+c to exit.")
        await interrupt_event.wait()
        logger.info("Shutting down")


if __name__ == "__main__":
    start_activities_worker()
