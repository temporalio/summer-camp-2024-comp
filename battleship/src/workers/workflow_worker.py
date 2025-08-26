import logging

import click
from temporalio.client import Client
from temporalio.worker import Worker

from src import coro, interrupt_event
from src.settings import TemporalClusterSettings
from src.utils.pydantic_converter import pydantic_data_converter
from src.workflows.game import Game
from src.workflows.player import Player

workflows = {
    Game.name: Game,
    Player.name: Player,
}


@click.command("workflow", context_settings={"show_default": True})
@click.option("-n", "--name", type=click.Choice(workflows.keys()), required=True)
@click.option("-v", "--verbose", is_flag=True)
@coro
async def start_workflow_worker(name, verbose):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("workflow")
    logger.setLevel(level=logging.DEBUG if verbose else logging.INFO)
    logger.debug(f"{verbose=}")

    logger.info("Initializing client...")
    settings = TemporalClusterSettings()
    client = await Client.connect(
        target_host=settings.host,
        namespace=settings.namespace,
        tls=settings.tls_config,
        data_converter=pydantic_data_converter,
    )
    logger.info(f'Client initialized! Connected to "{settings.host}"...')

    workflow = workflows.get(name)

    logger.info("Initializing worker...")
    async with Worker(
        client=client,
        task_queue=workflow.task_queue,
        workflows=[workflow],
        debug_mode=verbose,
    ):
        # Wait until interrupted
        logger.info(f"Worker initialized, ctrl+c to exit.")
        await interrupt_event.wait()
        logger.info("Shutting down")


if __name__ == "__main__":
    start_workflow_worker()
