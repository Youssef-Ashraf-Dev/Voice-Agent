# Voice Agent

This repository contains a voice-first conversational AI agent that uses Google's Gemini Live API for real-time speech-to-text, language understanding, and text-to-speech, with LiveKit handling the low-latency audio transport over WebRTC. A local RAG (Retrieval-Augmented Generation) module grounds the agent's responses in a specific knowledge base, ensuring it answers questions based on provided documentation.

## Architecture Overview

The system is composed of three main parts that run concurrently:

1.  **React Frontend (`my-voice-app/`):** A simple web interface that captures microphone audio and streams it to LiveKit. It also plays back the audio stream received from the agent.
2.  **Token Server (`token_server.py`):** A lightweight FastAPI server that issues JWTs (JSON Web Tokens) to the frontend, authorizing it to connect to a specific LiveKit room.
3.  **Voice Agent (`agent.py`):** A Python worker that connects to the same LiveKit room. It receives the audio stream, forwards it to the Gemini Live API, and executes tools (like RAG lookups) when requested by the model.

```
Browser (React + LiveKit SDK)
  ↕️  GET /getToken, WebRTC audio
Token Server (FastAPI) → issues LiveKit JWT
  ↕️  wss://<project>.livekit.cloud
LiveKit Cloud ↔ Voice Agent (Python worker)
  ↕️  streaming audio + function calls
Gemini Live API
  ↕️  lookup_company_info(query)
RAG Module (rag.py) → data/ecommerce.json
```

## Requirements

- Python 3.10+
- Node.js 18+ and npm 9+
- A Google AI Studio API key.
- A LiveKit Cloud project.

## Setup Instructions

1.  **Clone the repository and install dependencies:**
    ```powershell
    # Set up Python virtual environment
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

    # Install Python packages
    pip install -r requirements.txt

    # Install frontend packages
    cd my-voice-app
    npm install
    cd ..
    ```

2.  **Configure Environment Variables:**
    Create a file named `.env` in the root of the project directory and add your credentials. This file is ignored by Git.

    ```env
    # Get this from Google AI Studio
    GOOGLE_API_KEY=AI...

    # Get these from your LiveKit Cloud project settings
    LIVEKIT_URL=wss://<your-project-name>.livekit.cloud
    LIVEKIT_API_KEY=API...
    LIVEKIT_API_SECRET=...
    ```

3.  **Generate RAG Embeddings:**
    The first time you run the agent, it will automatically generate and cache the embeddings for the knowledge base (`data/ecommerce.json`). You can also pre-generate them with:
    ```powershell
    python -c "import rag; rag.get_stats()"
    ```
    If you modify `data/ecommerce.json`, you must delete the `embeddings_cache/` directory or run `python -c "import rag; rag.rebuild_cache()"` to force a regeneration.

## How to Run Locally

The system requires three separate terminal sessions to run correctly.

| Terminal | Command                       | Purpose                                     |
|----------|-------------------------------|---------------------------------------------|
| 1        | `python token_server.py`      | Serves the LiveKit authentication token.    |
| 2        | `python agent.py dev`         | Runs the voice agent worker.                |
| 3        | `cd my-voice-app; npm run dev` | Starts the frontend development server.     |

Once all three processes are running:
1.  Open your browser to `http://localhost:5173`.
2.  Click the "Start Voice Chat" button.
3.  Allow microphone access when prompted.
4.  Start speaking. The agent will listen and respond.
