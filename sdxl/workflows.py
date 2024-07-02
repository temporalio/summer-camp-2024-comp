from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        GenerateImageInput,
        create_folder,
        create_gif_from_images,
        generate_image,
    )


@workflow.defn
class AlphabetImageWorkflow:
    @workflow.run
    async def run(self, letter: str) -> str:
        await workflow.execute_activity(
            create_folder,
            start_to_close_timeout=timedelta(seconds=10),
        )

        return await workflow.execute_activity(
            generate_image,
            GenerateImageInput(letter=letter),
            start_to_close_timeout=timedelta(hours=2),
        )


@workflow.defn
class GifWorkflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            create_gif_from_images,
            start_to_close_timeout=timedelta(minutes=10),
        )
