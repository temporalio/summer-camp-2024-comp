import asyncio

from temporalio.client import Client

from workflows import AlphabetImageWorkflow


async def main() -> str:
    client = await Client.connect("localhost:7233")

    workflow_id = "alphabet-image-workflow-id"
    result = await client.execute_workflow(
        AlphabetImageWorkflow.run,
        id=workflow_id,
        task_queue="alphabet-image-workflow-task-queue",
    )
    print(f"Result: {result}")

    return "Gif created successfully."


if __name__ == "__main__":
    asyncio.run(main())
