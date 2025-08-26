from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        GenerateImageInput,
        create_folder,
        create_gif_from_images,
        generate_image,
        read_and_parse_file,
    )


@workflow.defn
class AlphabetImageWorkflow:
    @workflow.run
    async def run(self) -> str:
        await workflow.execute_activity(
            create_folder,
            start_to_close_timeout=timedelta(seconds=10),
        )

        letters = await workflow.execute_activity(
            read_and_parse_file,
            start_to_close_timeout=timedelta(seconds=10),
        )

        for letter in letters:
            await workflow.execute_activity(
                generate_image,
                GenerateImageInput(letter=letter),
                start_to_close_timeout=timedelta(minutes=20),
                heartbeat_timeout=timedelta(seconds=45),
            )

        return await workflow.execute_activity(
            create_gif_from_images,
            start_to_close_timeout=timedelta(minutes=10),
        )
