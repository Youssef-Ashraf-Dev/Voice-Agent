# 🤖 E-Commerce Voice Agent with RAG

A real-time voice AI assistant powered by **Google Gemini Live API**, **LiveKit**, and **FAISS-based RAG** for answering e-commerce customer support questions.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This project implements a voice-activated AI assistant that can answer customer questions about orders, shipping, returns, payments, and other e-commerce topics. The agent uses:

- **Google Gemini Live API** for real-time voice interaction
- **LiveKit** for WebRTC-based audio streaming
- **FAISS** for vector similarity search in the FAQ knowledge base
- **React + Vite** for the web interface

**Demo Flow:**
1. User opens the web UI and clicks "Start Voice Chat"
2. User speaks a question (e.g., "What's your return policy?")
3. Voice is streamed to the AI agent via LiveKit
4. Agent uses RAG to search the FAQ database
5. AI responds with accurate information using natural voice

---

## ✨ Features

- 🎙️ **Real-time voice interaction** with natural conversation flow
- 🔍 **RAG-powered answers** from a curated FAQ knowledge base (79 entries)
- 🧠 **Persistent embeddings cache** for fast startup (<1 second)
- 🌐 **Modern web UI** with React and LiveKit SDK
- 🔒 **Secure token-based authentication** with JWT
- 📊 **Agent state visualization** (speaking, listening, thinking, idle)
- ⚡ **High-quality audio** (96 kbps, echo cancellation, noise suppression)
- 🚀 **Production-ready architecture** with scalable components

---

## 🏗️ Architecture

### System Components

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

### How LiveKit Connects to Gemini Live API

1. **User speaks** → Browser captures audio via microphone
2. **LiveKit Client SDK** encodes audio to Opus codec and streams via WebSocket
3. **LiveKit Cloud** routes the audio stream to the Voice Agent
4. **Voice Agent** receives audio and passes it to `google.beta.realtime.RealtimeModel`
5. **Gemini Live API** processes the audio natively (no manual transcription needed)
6. **Gemini decides** if it needs more information and calls `lookup_company_info()` function
7. **RAG system** searches FAISS and returns relevant FAQ entries
8. **Gemini** generates a natural response incorporating the RAG data
9. **Audio response** flows back through LiveKit to the user's browser

### RAG Integration with Gemini Live API

The RAG system integrates through **function calling**:

```python
@function_tool
async def lookup_company_info(query: str):
    """
    Searches the company's FAQ database for information.
    Gemini AI calls this function automatically when it needs information.
    """
    return rag.search(query)
```

**Key Points:**
- Gemini Live API supports native function calling
- The agent registers `lookup_company_info` as an available tool
- Gemini's system prompt instructs it to ALWAYS use this tool for e-commerce questions
- When called, the function performs vector similarity search in FAISS
- Results are injected into Gemini's context for response generation
- Gemini synthesizes the information into natural spoken responses

---

## 📋 Prerequisites

### Required Software

- **Python 3.13** (or 3.10+)
- **Node.js 18+** and npm
- **Git**
- **Windows PowerShell** (or bash on Linux/Mac)

### Required API Keys & Accounts

1. **Google AI Studio API Key**
   - Sign up at: https://aistudio.google.com/
   - Create API key for Gemini
   - Set environment variable: `GOOGLE_API_KEY`

2. **LiveKit Account**
   - Sign up at: https://livekit.io/
   - Create a project
   - Get API Key, API Secret, and WebSocket URL
   - Set environment variables:
     - `LIVEKIT_API_KEY`
     - `LIVEKIT_API_SECRET`
     - `LIVEKIT_URL` (e.g., `wss://your-project.livekit.cloud`)

---

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/voice-agent.git
cd voice-agent
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# Google Gemini API
GOOGLE_API_KEY=your_google_api_key_here

# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud
```

**Security Note:** Never commit the `.env` file to Git. It's already in `.gitignore`.

### 4. Set Up Frontend

```bash
cd my-voice-app
npm install
cd ..
```

### 5. Initialize RAG System (Optional)

The RAG system will automatically create embeddings on first run. To verify:

```bash
python -c "import rag; print(rag.get_stats())"
```

Expected output:
```
RAG System Statistics:
- Total documents: 79
- Vector dimensions: 384
- Model: all-MiniLM-L6-v2
- Cache status: Created
```

---

## 🎮 Running the Application

You need **3 terminal windows** running simultaneously:

### Terminal 1: Token Server

```bash
cd "D:\Professional\Projects\Voice Agent\Voice-Agent"
python token_server.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2: Voice Agent

```bash
cd "D:\Professional\Projects\Voice Agent\Voice-Agent"
.\.venv\Scripts\Activate.ps1
python agent.py dev
```

**Expected output:**
```
INFO   livekit.agents   starting worker
INFO   livekit.agents   registered worker
```

### Terminal 3: Web UI

```bash
cd "D:\Professional\Projects\Voice Agent\Voice-Agent\my-voice-app"
npm run dev
```

**Expected output:**
```
VITE v7.2.4  ready in 300 ms
➜  Local:   http://localhost:5173/
```

### 6. Open the Application

1. Open browser and navigate to: **http://localhost:5173**
2. Click **"Start Voice Chat"**
3. Allow microphone access when prompted
4. Start speaking!

**Example questions to try:**
- "What's your return policy?"
- "How long does shipping take?"
- "What payment methods do you accept?"
- "Can I track my order?"
- "Do you offer gift wrapping?"

---

## 📁 Project Structure

```
Voice-Agent/
├── agent.py                          # Main voice agent entrypoint
├── token_server.py                   # JWT token generation server
├── rag.py                            # RAG system with FAISS
├── requirements.txt                  # Python dependencies
├── .env                              # Environment variables (not committed)
├── .gitignore                        # Git ignore rules
│
├── data/
│   └── ecommerce.json                # Knowledge base (79 FAQs)
│
├── embeddings_cache/
│   ├── faiss_index.bin               # FAISS vector index (~122 KB)
│   └── metadata.pkl                  # Document metadata (~45 KB)
│
├── my-voice-app/                     # React frontend
│   ├── package.json                  # Node.js dependencies
│   ├── vite.config.js                # Vite configuration
│   ├── index.html                    # HTML entry point
│   └── src/
│       ├── main.jsx                  # React entry point
│       ├── App.jsx                   # Main React component
│       └── App.css                   # Styling
│
└── Documentation/
    ├── README.md                     # This file
    ├── SYSTEM_ARCHITECTURE_EXPLAINED.md   # Complete system guide
    ├── REACT_UI_DETAILED_GUIDE.md         # React/Frontend guide
    ├── RAG_FLOW_EXPLAINED.md              # RAG system explanation
    ├── RAG_RETRIEVAL_DOCUMENTATION.md     # RAG retrieval examples
    ├── EMBEDDING_TESTING_GUIDE.md         # Embedding accuracy tests
    └── UI_SETUP_GUIDE.md                  # UI setup instructions
```

---

## 🔧 How It Works

### Voice Interaction Flow

```
1. User speaks: "What's your return policy?"
   ↓
2. Browser captures audio → LiveKit Client SDK
   ↓
3. WebSocket stream → LiveKit Cloud
   ↓
4. LiveKit routes → Voice Agent
   ↓
5. Agent forwards → Gemini Live API
   ↓
6. Gemini understands query and calls: lookup_company_info("return policy")
   ↓
7. RAG System:
   - Embeds query: "return policy" → 384-dim vector
   - Searches FAISS: Find top-3 similar vectors
   - Returns: Q&A about 30-day returns, original payment method, etc.
   ↓
8. Gemini receives RAG results
   ↓
9. Gemini generates natural response: "Our return policy allows..."
   ↓
10. Gemini converts to speech (audio)
   ↓
11. Agent → LiveKit → Browser
   ↓
12. User hears the response
```

### RAG Retrieval Process

**Step-by-step:**

1. **Query arrives**: `"return policy"`
2. **Embed query**: 
   ```python
   query_embedding = model.encode("return policy")
   # Result: [0.123, -0.456, 0.789, ...] (384 dimensions)
   ```
3. **Search FAISS**:
   ```python
   distances, indices = faiss_index.search(query_embedding, k=3)
   ```
4. **Retrieve documents**: Get top-3 most similar FAQ entries
5. **Format results**:
   ```
   Q: What is your return policy?
   A: You can return items within 30 days of delivery...
   
   Q: How do I initiate a return?
   A: Log into your account, go to Orders, click Return...
   ```
6. **Return to Gemini**: Gemini uses this as context for its response

### Agent Instructions

The agent is configured with clear boundaries:

```python
agent = Agent(
    instructions=(
        "You are a helpful FAQ assistant. "
        "You ONLY have access to general FAQ information. "
        "You CANNOT access specific customer orders or accounts. "
        "Always use the lookup_company_info tool for e-commerce questions. "
        "Never ask for order numbers or personal information."
    ),
)
```

This ensures the agent:
- ✅ Answers general policy questions
- ✅ Uses RAG for accurate information
- ❌ Doesn't pretend to access customer data
- ❌ Doesn't ask for information it can't use

---

## 📚 Documentation

### Detailed Guides

1. **[SYSTEM_ARCHITECTURE_EXPLAINED.md](SYSTEM_ARCHITECTURE_EXPLAINED.md)**
   - Complete system overview
   - Component breakdown
   - WebSocket and audio flow
   - For technical interviews

2. **[REACT_UI_DETAILED_GUIDE.md](REACT_UI_DETAILED_GUIDE.md)**
   - React fundamentals for backend developers
   - Component explanation with Python equivalents
   - State management deep dive

3. **[RAG_FLOW_EXPLAINED.md](RAG_FLOW_EXPLAINED.md)**
   - How RAG integrates with Gemini
   - Vector embeddings explained
   - FAISS indexing process

4. **[RAG_RETRIEVAL_DOCUMENTATION.md](RAG_RETRIEVAL_DOCUMENTATION.md)**
   - Real retrieval examples
   - Similarity scores and evidence
   - Query optimization tips

5. **[EMBEDDING_TESTING_GUIDE.md](EMBEDDING_TESTING_GUIDE.md)**
   - How to validate embedding accuracy
   - Test script usage
   - Performance benchmarks

6. **[UI_SETUP_GUIDE.md](UI_SETUP_GUIDE.md)**
   - Step-by-step UI setup
   - 3-terminal workflow
   - Browser compatibility

---

## 🐛 Troubleshooting

### Common Issues

#### "Failed to connect" in web UI

**Problem**: Token server not running

**Solution**:
```bash
python token_server.py
```

#### "Agent not responding"

**Problem**: Voice agent not running or not connected to LiveKit

**Solution**:
```bash
.\.venv\Scripts\Activate.ps1
python agent.py dev
```

Check output for:
```
INFO   livekit.agents   registered worker
```

#### "Module not found" errors

**Problem**: Virtual environment not activated or dependencies not installed

**Solution**:
```bash
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Audio is choppy or unclear

**Problem**: Network latency or browser compatibility

**Solution**:
- Use **Google Chrome** (best WebRTC support)
- Check your internet connection
- Ensure firewall allows WebSocket connections
- Audio settings are optimized in `App.jsx` (96 kbps, echo cancellation)

#### RAG returns "No relevant information found"

**Problem**: Query doesn't match FAQ topics

**Solution**:
- Check `data/ecommerce.json` for available topics
- Try rephrasing the question
- Add more FAQs to the knowledge base

#### Environment variables not loading

**Problem**: `.env` file not found or formatted incorrectly

**Solution**:
```bash
# Verify .env file exists
ls .env

# Check format (no spaces around =)
GOOGLE_API_KEY=your_key_here
LIVEKIT_API_KEY=your_key_here
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Rotate API keys regularly** - Especially if exposed
3. **Use token expiration** - Token server sets 10-minute expiry
4. **Limit CORS** - Token server only allows localhost in development
5. **Validate inputs** - Agent instructions prevent prompt injection

---

## 📈 Performance

### RAG System

- **First run**: 3-5 seconds (creates embeddings)
- **Subsequent runs**: <1 second (loads from cache)
- **Search latency**: <10 milliseconds per query
- **Cache size**: ~170 KB (79 documents)

### Voice Latency

- **User speaks → Agent hears**: ~200-500ms
- **RAG search**: <10ms
- **Gemini processing**: ~500-1000ms
- **Agent speaks → User hears**: ~200-500ms
- **Total round-trip**: ~1-2 seconds

### Audio Quality

- **Codec**: Opus (WebRTC standard)
- **Bitrate**: 96 kbps (high quality)
- **Sample rate**: 24 kHz (Gemini native)
- **Echo cancellation**: Enabled
- **Noise suppression**: Enabled

---

## 🚀 Production Deployment

### Considerations

1. **Scale LiveKit**: Use LiveKit Cloud or self-hosted cluster
2. **Database**: Move from JSON to PostgreSQL/MongoDB for larger FAQ sets
3. **Vector DB**: Consider Pinecone, Weaviate, or Qdrant for production RAG
4. **CDN**: Serve React build through CloudFlare or AWS CloudFront
5. **Monitoring**: Add logging, metrics (Prometheus), and error tracking (Sentry)
6. **Load balancing**: Use multiple agent instances for high concurrency

### Environment Variables for Production

```env
# Use production LiveKit URL
LIVEKIT_URL=wss://production.livekit.cloud

# Enable HTTPS for token server
TOKEN_SERVER_URL=https://api.yourdomain.com

# Set CORS to your production domain
ALLOWED_ORIGINS=https://yourdomain.com
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Authors

- **Your Name** - Initial work

---

## 🙏 Acknowledgments

- **LiveKit** - Real-time audio infrastructure
- **Google Gemini** - AI language model with native voice support
- **Sentence Transformers** - Embedding models for RAG
- **FAISS** - Efficient vector similarity search
- **React Team** - Frontend framework

---

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Check the documentation in the `/Documentation` folder
- Review the troubleshooting section above

---

**Built with ❤️ using Google Gemini Live API, LiveKit, and FAISS**
