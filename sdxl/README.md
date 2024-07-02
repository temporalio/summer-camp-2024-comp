# Alphabet Image Generation with Temporal

This project demonstrates the use of Temporal for orchestrating the generation of images representing letters A-Z using the Stable Diffusion XL (SDXL) model with a weighted LoRA.
The workflow generates individual images for each letter and compiles them into an animated GIF.

## Components

1. **Model Loading**: The SDXL model is loaded once outside the activity function and reused. A weighted LoRA specific to each letter is applied.
2. **Activity**: Generates the image for each letter and saves it to the `alphabet_images` directory.
3. **Workflow**:
   - `AlphabetImageWorkflow` iterates through each letter, calling the `generate_image` activity.
   - `GifWorkflow` gathers all images and generates a GIF.
4. **Main Function**: Sets up the Temporal client and worker, and runs the workflows.

## Installation and Setup

You will need to run the Activities on a GPU.

Create and activate the virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```sh
pip install -r requirements.txt
```

Start the Temporal server:

```sh
temporal server start-dev
```

Start the worker and initiate the workflows:

```sh
python worker.py
python starter.py
```