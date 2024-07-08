import os
import random
from dataclasses import dataclass

import imageio.v3 as iio
import torch
from diffusers import DiffusionPipeline
from temporalio import activity

# Constants
PIPELINE_MODEL = "stabilityai/sdxl-turbo"
LORA_WEIGHTS = "CiroN2022/toy-face"
LORA_WEIGHT_NAME = "toy_face_sdxl.safetensors"
ADAPTER_NAME = "toy"
FOLDER_NAME = "alphabet_images"
LORA_SCALE = 8
INFERENCE_STEPS = 10
GUIDANCE_SCALE = 1
IMAGE_HEIGHT = 512
IMAGE_WIDTH = 512
FILE_NAME = "file.txt"

# Set environment variable for CUDA memory management
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Load the pipeline
try:
    pipe = DiffusionPipeline.from_pretrained(
        PIPELINE_MODEL, torch_dtype=torch.float16
    ).to("cuda")
    print("Stable Diffusion pipeline loaded")
    pipe.load_lora_weights(
        LORA_WEIGHTS,
        weight_name=LORA_WEIGHT_NAME,
        adapter_name=ADAPTER_NAME,
    )
    # Enable attention slicing for memory efficiency
    pipe.enable_attention_slicing()
except Exception as e:
    print(f"Error loading pipeline: {e}")
    raise


@dataclass
class GenerateImageInput:
    letter: str


@activity.defn
async def create_folder() -> str:
    try:
        if not os.path.exists(FOLDER_NAME):
            os.makedirs(FOLDER_NAME)
            activity.logger.info(f"Folder {FOLDER_NAME} created")
            return "Folder created"
        activity.logger.info(f"Folder {FOLDER_NAME} exists")
        return "Folder exists"
    except Exception as e:
        activity.logger.error(f"Error creating folder: {e}")
        raise


@activity.defn
async def read_and_parse_file() -> list:
    try:
        with open(FILE_NAME, "r") as file:
            letters = file.read().strip()
            activity.logger.info(f"Letters read from {FILE_NAME}: {letters}")
            return list(letters)
    except Exception as e:
        activity.logger.error(f"Error reading file: {e}")
        raise


@activity.defn
async def generate_image(input: GenerateImageInput) -> str:
    letter = input.letter
    activity.logger.info(f"Running activity with parameter {letter}")

    # Clear CUDA cache
    torch.cuda.empty_cache()

    # Generate a random seed for each image
    random_seed = random.randint(0, 9999)
    activity.logger.info(f"Using random seed: {random_seed}")

    # Generate the image based on the prompt
    prompt = f"toy_face highly detalied letter {letter} prominently displayed."
    generator = torch.Generator(device="cuda").manual_seed(random_seed)
    result = pipe(
        prompt=prompt,
        num_inference_steps=INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        height=IMAGE_HEIGHT,
        width=IMAGE_WIDTH,
        generator=generator,
    )
    image = result.images[0]
    activity.heartbeat(f"Image generated for letter {letter}")
    print(f"Image generated for letter {letter}")

    # Save the image to the folder
    image_path = os.path.join(FOLDER_NAME, f"{letter}.png")
    image.save(image_path)
    activity.logger.info(f"Image saved at {image_path}")

    return f"Image generated and saved for letter {letter}"


@activity.defn
async def create_gif_from_images() -> str:
    try:
        # Get a sorted list of image paths
        image_paths = sorted(
            [
                os.path.join(FOLDER_NAME, filename)
                for filename in os.listdir(FOLDER_NAME)
                if filename.endswith(".png")
            ]
        )

        # Read all images into a list of frames
        frames = [iio.imread(image_path) for image_path in image_paths]

        output_path = os.path.join(FOLDER_NAME, "alphabet.gif")
        iio.imwrite(output_path, frames, duration=0.5, loop=0)

        return f"Animated GIF created and saved at {output_path}"
    except Exception as e:
        activity.logger.error(f"Error creating GIF: {e}")
        raise
