# Alphabet Image Generation with Temporal

This project demonstrates the use of Temporal for orchestrating the generation of images representing letters A-Z using the Stable Diffusion XL (SDXL) model with a weighted LoRA.
The workflow generates individual images for each letter and compiles them into an animated GIF.

## Components

1. **Model Loading**: The SDXL model is loaded once outside the activity function and reused. A weighted LoRA specific to each letter is applied.
2. **Activities**:
   - `create_folder`: Ensures the `alphabet_images` directory exists.
   - `read_and_parse_file`: Reads letters from `file.txt`.
   - `generate_image`: Generates the image for each letter and saves it to the `alphabet_images` directory.
   - `create_gif_from_images`: Compiles the images into an animated GIF.
3. **Workflow**:
   - `AlphabetImageWorkflow`: Reads letters from the file, calls `generate_image` for each letter, and finally creates a GIF from the generated images.
4. **Main Function**: Sets up the Temporal client and worker, and runs the workflow.

## Installation and Setup

You will need to run the activities on a GPU.

### Prerequisites

- [Temporal CLI](https://docs.temporal.io/docs/cli/)
- Python 3.8 or later

### Install Temporal CLI

```sh
curl -sSf https://temporal.download/cli.sh | sh
```

### Create and activate the virtual environment

```sh
python3 -m venv .venv
source .venv/bin/activate
```

### Install the required packages

```sh
pip install -r requirements.txt
```

### Start the Temporal server

```sh
temporal server start-dev
```

### Prepare the `file.txt`

Ensure you have a `file.txt` in the root directory with the following content:

```txt
ABCDEFGHIJKLMNOPQRSTUVWXYZ
```

### Start the worker and initiate the workflow

Start the worker:

```sh
python worker.py
```

Initiate the workflow:

```sh
python starter.py
```

### Result

The generated images will be saved in the `alphabet_images` directory, and an animated GIF will be created from these images.

### Troubleshooting

- Ensure your GPU is properly configured and available.
- Verify the Temporal server is running and accessible.
- Check the logs for any errors during model loading or image generation.
