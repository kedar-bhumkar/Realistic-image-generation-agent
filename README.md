# Realistic-image-generation-agent

Agentic workflow for Nano Banana Pro , Qwen image, GPT-image, Flux image, designed to orchestrate image generation using Replicate, OpenAI, n8n, Supabase.

## Features

- **Image Generation Workflow**: Automates generation tasks with customizable parameters.
- **Remote Storage**: Supports saving results to Google Drive.
- **Background Processing**: Runs workflows asynchronously via FastAPI background tasks.
- **Secure Access**: Protected by Bearer token authentication.

## Prerequisites

- Python 3.8+
- [Supabase](https://supabase.com/) account
- [OpenAI](https://openai.com/) API Key
- [Replicate](https://replicate.com/) API Token
- Google Cloud credentials for Drive access (if using remote save)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd nano-banana-pro-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Copy `env.example` to `.env` and fill in your credentials.
   ```bash
   cp env.example .env
   ```
   
   Required variables:
   - `SUPABASE_URL`: Your Supabase project URL.
   - `SUPABASE_KEY`: Your Supabase anonymous key.
   - `OPENAI_API_KEY`: API key for OpenAI.
   - `REPLICATE_API_TOKEN`: API token for Replicate.
   - `API_AUTH_TOKEN`: Secret token used to authenticate requests to this API.

## Usage

### Starting the Server

Run the FastAPI server using uvicorn:

```bash
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`.

### API Endpoints

#### Health Check
- **GET** `/`
- Returns status of the API.

#### Trigger Workflow
- **POST** `/run`
- **Headers**: 
  - `Authorization: Bearer <YOUR_API_AUTH_TOKEN>`
- **Body** (JSON):
  ```json
  {
    "save_remotely": true,
    "drive_folder_id": "optional_folder_id",
    "category": "optional_category",
    "min_val": 1,
    "max_val": 10,
    "resolution": "1024x1024",
    "aspect_ratio": "1:1",
    "mode": "standard",
    "model_version": "google/nano-banana-pro",
    "image_urls": [],
    "prompts": []
  }
  ```

## Project Structure

- `app.py`: FastAPI application entry point.
- `main.py`: Main logic wrapper invoking the orchestrator.
- `nano-banana-pro.py`: Legacy image generation logic.
- `src/`: Core logic modules.
  - `orchestrator.py`: Manages the workflow steps.
  - `database.py`: Database interactions (Supabase).
  - `llm.py`: Language model interactions.
  - `utils.py`: Utility functions.
- `output/`: Generated results (ignored by git).
- `input/`: Input files (ignored by git).

