import uuid

from temporalio.client import Client

from src import coro
from src.workflows.game import Game


@coro
async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    handle = await client.start_workflow(
        workflow=Game.run,
        id=str(uuid.uuid4()),
        task_queue="game-tasks",
    )

    print(f"Started workflow. Workflow ID: {handle.id}, RunID {handle.result_run_id}")

    result = await handle.result()

    print(f"Result: {result}")


if __name__ == "__main__":
    main()
