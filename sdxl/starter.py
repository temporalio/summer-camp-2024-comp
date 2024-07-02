import asyncio

from temporalio.client import Client

from workflows import AlphabetImageWorkflow, GifWorkflow


async def main() -> str:
    client = await Client.connect("localhost:7233")
    letters: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for letter in letters:
        workflow_id = f"alphabet-image-workflow-id-{letter}"
        result = await client.execute_workflow(
            AlphabetImageWorkflow.run,
            letter,
            id=workflow_id,
            task_queue="alphabet-image-workflow-task-queue",
        )
        print(f"Result for {letter}: {result}")
    print("All images executed successfully.")
    await client.execute_workflow(
        GifWorkflow.run,
        id="gif-workflow",
        task_queue="alphabet-image-workflow-task-queue",
    )

    return print("Gif created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
