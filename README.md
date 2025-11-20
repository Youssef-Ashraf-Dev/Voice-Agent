# E-Commerce Voice Agent with RAG

A production-ready real-time voice AI assistant powered by Google Gemini Live API, LiveKit, and FAISS-based RAG for intelligent e-commerce customer support.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running Locally](#running-locally)
- [Project Structure](#project-structure)
- [Technical Documentation](#technical-documentation)

---

## Overview

This system implements an intelligent voice assistant that provides real-time responses to customer inquiries about e-commerce operations including orders, shipping, returns, payments, and policies. The architecture combines:

- **Google Gemini Live API** (`gemini-live-2.5-flash-preview`) for native voice processing
- **LiveKit** for WebRTC-based real-time audio streaming infrastructure
- **FAISS** vector database for semantic similarity search over FAQ knowledge base
- **React + Vite** frontend with LiveKit Client SDK

**Key Capabilities:**
- Real-time bidirectional voice communication with <2s latency
- RAG-enhanced responses using vector similarity search (384-dimensional embeddings)
- Persistent embeddings cache for sub-second initialization
- JWT-based secure authentication
- High-fidelity audio (96 kbps Opus codec, echo cancellation, noise suppression)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         USER BROWSER                         │
│                  (React + LiveKit Client SDK)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ① HTTP: GET /getToken
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      TOKEN SERVER                            │
│                  (FastAPI - Port 8000)                       │
│              Issues JWT tokens for LiveKit                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ② Returns: {token, url}
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      LIVEKIT CLOUD                           │
│                   (WebRTC/WebSocket SFU)                     │
│              Routes audio streams bidirectionally            │
└───────────┬──────────────────────────────┬──────────────────┘
            │                              │
            │ ③ Audio Stream               │ ④ Audio Stream
            ↓                              ↑
┌─────────────────────────────────────────────────────────────┐
│                       VOICE AGENT                            │
│           (Python + LiveKit Agents SDK)                      │
│    • Manages conversation with AgentSession                  │
│    • Connects to Gemini Live API                             │
│    • Provides lookup_company_info function tool              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ⑤ Audio + Function Calls
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    GOOGLE GEMINI LIVE API                    │
│               (gemini-live-2.5-flash-preview)                │
│    • Speech-to-Text (user audio → text)                      │
│    • Natural Language Understanding                          │
│    • Function calling (decides when to call RAG)             │
│    • Text-to-Speech (response → audio)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ⑥ Function Call: lookup_company_info(query)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                       RAG SYSTEM                             │
│                    (rag.py + FAISS)                          │
│    • Embeds user query with all-MiniLM-L6-v2                │
│    • Searches FAISS vector database (79 embeddings)          │
│    • Returns top-3 relevant Q&A pairs                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ ⑦ Reads FAQ data
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                            │
│                  (data/ecommerce.json)                       │
│    79 FAQ entries about orders, shipping, returns, etc.      │
└─────────────────────────────────────────────────────────────┘
```

### LiveKit Connection to Gemini Live API

**Audio Flow Pipeline:**

1. **User Input Capture**
   - Browser microphone API captures raw audio
   - LiveKit Client SDK encodes to Opus codec (efficient compression for voice)
   - Audio transmitted via WebSocket to LiveKit Cloud SFU (Selective Forwarding Unit)

2. **Agent Processing**
   - LiveKit Cloud routes audio stream to Voice Agent (Python worker)
   - Agent forwards stream to `google.beta.realtime.RealtimeModel`
   - Gemini Live API processes audio natively (integrated speech-to-text, no separate transcription)

3. **Natural Language Understanding**
   - Gemini performs intent recognition on transcribed speech
   - Evaluates if query requires knowledge base lookup
   - Triggers function call: `lookup_company_info(query)` when needed

4. **Response Generation**
   - Audio response synthesized by Gemini (integrated text-to-speech)
   - Agent receives audio stream from Gemini
   - LiveKit routes audio back to browser for playback

**Connection Characteristics:**
- Protocol: WebSocket (WSS) for persistent bidirectional communication
- Latency: ~200-500ms browser↔LiveKit, ~500-1000ms Gemini processing
- Audio: 24 kHz sample rate, 96 kbps bitrate, mono channel

### RAG Integration Architecture

**Function Calling Mechanism:**

The RAG system integrates via Gemini's native function calling capability:

```python
@function_tool
async def lookup_company_info(query: str):
    """
    Searches the company's FAQ database for information about orders, 
    shipping, returns, payments, and policies.
    
    Args:
        query: User's question or keywords
    
    Returns:
        Formatted Q&A pairs from knowledge base
    """
    return rag.search(query, top_k=3)
```

**Integration Flow:**

1. **Function Registration**
   - Agent registers `lookup_company_info` as available tool during initialization
   - Function signature and docstring sent to Gemini for decision-making context

2. **Query Processing**
   - User query: *"What's your return policy?"*
   - Gemini analyzes intent and determines function call needed
   - Invokes: `lookup_company_info("return policy")`

3. **Vector Search Execution**
   ```python
   # In rag.py
   query_embedding = model.encode(query)  # 384-dim vector via all-MiniLM-L6-v2
   distances, indices = faiss_index.search(query_embedding, k=3)
   results = [documents[i] for i in indices[0]]
   ```

4. **Context Injection**
   - RAG returns top-3 semantically similar Q&A pairs
   - Results injected into Gemini's context window
   - Gemini synthesizes natural language response incorporating retrieved information

5. **Response Delivery**
   - Gemini generates contextually-aware answer
   - Converted to speech and streamed back to user

**RAG System Configuration:**
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Vector Index**: FAISS IndexFlatL2 (L2 distance metric)
- **Knowledge Base**: 79 FAQ entries from `data/ecommerce.json`
- **Retrieval**: Top-3 results with cosine similarity ranking
- **Cache**: Persistent storage in `embeddings_cache/` for instant loading

---

## Prerequisites

### Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10 - 3.13 | Backend agent and RAG system |
| Node.js | 18+ | Frontend development server |
| npm | 9+ | JavaScript package management |
| Git | Latest | Version control |

### API Keys and Service Accounts

#### 1. Google AI Studio API Key

**Purpose**: Authenticates requests to Gemini Live API for voice processing

**Setup Steps:**
1. Navigate to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with Google account
3. Click "Get API Key" → "Create API Key"
4. Copy the generated key (format: `AIzaSy...`)
5. Store securely for environment configuration

**Permissions Required**: Gemini API access

#### 2. LiveKit Cloud Account

**Purpose**: Provides WebRTC infrastructure for real-time audio streaming

**Setup Steps:**
1. Create account at [LiveKit Cloud](https://livekit.io/)
2. Create new project (e.g., "voice-agent-production")
3. Navigate to project settings → API Keys
4. Generate new API key pair:
   - **API Key**: Identifier (format: `APIxxx...`)
   - **API Secret**: Secret key (format: `xxx...`) - treat as password
5. Copy WebSocket URL from project dashboard:
   - Format: `wss://your-project-name.livekit.cloud`

**Configuration Details:**
- **API Key**: Used for server-side token generation
- **API Secret**: Used for signing JWT tokens (never expose client-side)
- **WebSocket URL**: Connection endpoint for LiveKit rooms

---

## Setup Instructions

### 1. Repository Setup

```bash
git clone https://github.com/yourusername/voice-agent.git
cd voice-agent
```

### 2. Python Environment Configuration

**Create and activate virtual environment:**

```bash
# Create isolated Python environment
python -m venv .venv

# Activate environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux/macOS:
source .venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `fastapi` + `uvicorn`: Token server (JWT generation)
- `livekit` + `livekit-agents` + `livekit-plugins-google`: Voice agent framework
- `google-generativeai`: Gemini API client
- `faiss-cpu` + `sentence-transformers`: RAG system (vector search + embeddings)
- `PyJWT`: Token signing
- `python-dotenv`: Environment variable loading

### 3. Environment Variables Configuration

Create `.env` file in project root directory:

```bash
# .env file (do NOT commit to version control)

# Google Gemini API Configuration
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# LiveKit Cloud Configuration
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LIVEKIT_URL=wss://your-project-name.livekit.cloud
```

**Environment Variable Details:**

| Variable | Description | Example Format | Required |
|----------|-------------|----------------|----------|
| `GOOGLE_API_KEY` | Google AI Studio API key for Gemini | `AIzaSy...` | Yes |
| `LIVEKIT_API_KEY` | LiveKit project API identifier | `APIxxx...` | Yes |
| `LIVEKIT_API_SECRET` | LiveKit secret for JWT signing | Base64 string | Yes |
| `LIVEKIT_URL` | WebSocket URL for LiveKit connection | `wss://xxx.livekit.cloud` | Yes |

**Security Best Practices:**
- Never commit `.env` file (already in `.gitignore`)
- Rotate keys if accidentally exposed
- Use separate keys for development/production
- Restrict API key permissions to minimum required scope

### 4. Frontend Setup

```bash
cd my-voice-app
npm install
cd ..
```

**Installs:**
- `react` + `react-dom`: UI framework
- `livekit-client` + `@livekit/components-react`: LiveKit SDK
- `vite`: Development server and build tool

### 5. Verify RAG System Initialization

The RAG system automatically generates embeddings on first execution. To verify setup:

```bash
python -c "import rag; print(rag.get_stats())"
```

**Expected output:**
```
RAG System Statistics:
- Total documents: 79
- Vector dimensions: 384
- Model: all-MiniLM-L6-v2
- Cache status: Loaded from disk (or Created on first run)
- Cache location: embeddings_cache/
- Index size: ~122 KB
```

**First Run Behavior:**
- Downloads `all-MiniLM-L6-v2` model (~90 MB)
- Generates 79 embeddings from `data/ecommerce.json`
- Creates FAISS index and saves to `embeddings_cache/`
- Subsequent runs load from cache (<1 second)

---

## Running Locally

The system requires **3 concurrent processes** running in separate terminals:

### Terminal 1: Token Server

**Purpose**: Generates JWT tokens for LiveKit room authentication

```bash
# Navigate to project root
cd voice-agent

# Start FastAPI server
python token_server.py
```

**Expected Output:**
```
INFO:     Started server process [PID: xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verification:**
- Server listens on `http://localhost:8000`
- Endpoint: `GET /getToken` returns `{token: string, url: string}`
- CORS enabled for `http://localhost:5173` (development only)

**Troubleshooting:**
- Port 8000 already in use: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Linux/Mac)
- Import errors: Verify virtual environment activated and dependencies installed

---

### Terminal 2: Voice Agent

**Purpose**: Manages LiveKit-Gemini connection and RAG function calls

```bash
# Navigate to project root
cd voice-agent

# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux/macOS

# Start agent in development mode
python agent.py dev
```

**Expected Output:**
```
DEBUG  asyncio          Using proactor: IocpProactor
INFO   livekit.agents   starting worker {"version": "1.3.2"}
INFO   livekit.agents   registered worker {"id": "AW_xxxxx", "region": "..."}
```

**Initialization Steps:**
1. Loads environment variables from `.env`
2. Initializes RAG system (loads FAISS index and embeddings)
3. Connects to LiveKit Cloud using WebSocket
4. Registers as available agent worker
5. Waits for room join events

**Verification:**
- Log shows "registered worker" with unique ID
- RAG system loads in <1 second (from cache)
- No authentication errors with Google/LiveKit APIs

**Troubleshooting:**
- `ModuleNotFoundError`: Check virtual environment activation
- Authentication errors: Verify `.env` file exists and contains valid keys
- Connection timeout: Check network/firewall allows WSS connections to LiveKit

---

### Terminal 3: Frontend Development Server

**Purpose**: Serves React UI for browser access

```bash
# Navigate to frontend directory
cd voice-agent/my-voice-app

# Start Vite development server
npm run dev
```

**Expected Output:**
```
VITE v7.2.4  ready in 269 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

**Verification:**
- Server accessible at `http://localhost:5173`
- Hot module replacement (HMR) enabled for live code updates

**Troubleshooting:**
- Port 5173 in use: Vite auto-increments (check output for actual port)
- Build errors: Delete `node_modules/` and run `npm install` again

---

### Testing the Complete System

1. **Open Browser**
   - Navigate to `http://localhost:5173`
   - Use Chrome/Edge for best WebRTC compatibility

2. **Initiate Voice Session**
   - Click "Start Voice Chat" button
   - Browser requests token from `localhost:8000/getToken`
   - UI connects to LiveKit using returned JWT token
   - Allow microphone access when prompted

3. **Verify Connection**
   - UI shows "Connected" state
   - Voice Agent terminal shows "room joined" log
   - Agent greets user with introduction

4. **Test Voice Interaction**
   ```
   User: "What's your return policy?"
   → Agent processes via Gemini
   → Calls lookup_company_info("return policy")
   → RAG searches FAISS index
   → Returns relevant Q&A
   → Agent speaks natural response
   ```

5. **Monitor Logs**
   - Token Server: Shows token generation requests
   - Voice Agent: Shows RAG tool calls and responses
   - Browser Console (F12): Shows LiveKit connection events

**Sample Test Queries:**
- "What payment methods do you accept?"
- "How long does standard shipping take?"
- "Can I return items after 30 days?"
- "Do you offer international shipping?"
- "How do I track my order?"

**Performance Expectations:**
- Connection establishment: <2 seconds
- Speech recognition latency: 200-500ms
- RAG search time: <10ms
- End-to-end response: 1-2 seconds

---

## Project Structure

```
voice-agent/
│
├── agent.py                          # Voice agent entrypoint (LiveKit worker)
├── token_server.py                   # FastAPI server for JWT token generation
├── rag.py                            # RAG system: FAISS indexing + search
├── requirements.txt                  # Python dependencies (major packages only)
├── .env                              # Environment variables (not version controlled)
├── .env.example                      # Template for environment configuration
├── .gitignore                        # Git exclusions
│
├── data/
│   └── ecommerce.json                # Knowledge base: 79 FAQ Q&A pairs
│
├── embeddings_cache/                 # Persistent vector storage (auto-generated)
│   ├── faiss_index.bin               # FAISS L2 index (~122 KB)
│   └── metadata.pkl                  # Document metadata (~45 KB)
│
├── my-voice-app/                     # React frontend application
│   ├── package.json                  # Node.js dependencies
│   ├── vite.config.js                # Vite build configuration
│   ├── index.html                    # HTML entry point
│   └── src/
│       ├── main.jsx                  # React initialization
│       ├── App.jsx                   # Main UI component (LiveKitRoom + state)
│       └── App.css                   # Component styling
│
└── [Documentation Files]
    ├── SYSTEM_ARCHITECTURE_EXPLAINED.md   # Complete architecture deep-dive
    ├── REACT_UI_DETAILED_GUIDE.md         # Frontend guide for backend developers
    ├── RAG_FLOW_EXPLAINED.md              # RAG integration with Gemini
    ├── RAG_RETRIEVAL_DOCUMENTATION.md     # Retrieval examples and benchmarks
    ├── EMBEDDING_TESTING_GUIDE.md         # Embedding accuracy validation
    └── UI_SETUP_GUIDE.md                  # Step-by-step UI instructions
```

**Core Components:**

| File | Purpose | Key Technologies |
|------|---------|------------------|
| `agent.py` | Voice agent worker that connects LiveKit to Gemini | `livekit-agents`, `google.beta.realtime` |
| `token_server.py` | Generates JWT tokens for client authentication | `fastapi`, `PyJWT`, `livekit` |
| `rag.py` | Vector search system for FAQ retrieval | `faiss-cpu`, `sentence-transformers` |
| `my-voice-app/` | Browser-based UI for voice interaction | `react`, `livekit-client` |

---

## Technical Documentation

### Comprehensive Guides

| Document | Description | Target Audience |
|----------|-------------|-----------------|
| [SYSTEM_ARCHITECTURE_EXPLAINED.md](SYSTEM_ARCHITECTURE_EXPLAINED.md) | Complete system architecture, component breakdown, WebSocket/audio flow | Technical reviewers, architects |
| [RAG_FLOW_EXPLAINED.md](RAG_FLOW_EXPLAINED.md) | RAG integration with Gemini Live API, vector embeddings, FAISS indexing | ML engineers, backend developers |
| [RAG_RETRIEVAL_DOCUMENTATION.md](RAG_RETRIEVAL_DOCUMENTATION.md) | Real retrieval examples, similarity metrics, query optimization | Data scientists, QA engineers |
| [REACT_UI_DETAILED_GUIDE.md](REACT_UI_DETAILED_GUIDE.md) | React fundamentals with Python equivalents, component architecture | Backend developers learning frontend |
| [EMBEDDING_TESTING_GUIDE.md](EMBEDDING_TESTING_GUIDE.md) | Embedding accuracy validation, test procedures, benchmarks | ML engineers, testers |
| [UI_SETUP_GUIDE.md](UI_SETUP_GUIDE.md) | Step-by-step UI setup, 3-terminal workflow, browser compatibility | Developers, deployers |

---

## License

MIT License - See LICENSE file for details

---

## Support

- **Issues**: Open GitHub issue for bug reports or feature requests
- **Documentation**: Refer to guides in repository root
- **Security**: Report vulnerabilities privately to maintainers

---

**Technology Stack**: Google Gemini Live API • LiveKit • FAISS • React • FastAPI
