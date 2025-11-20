# System Architecture

This document explains how the voice agent system integrates LiveKit, Google Gemini Live API, and RAG for real-time voice interactions.

---

## System Overview

The architecture consists of three primary components working together:

```
┌─────────────────────────────────────────────────────────────┐
│                         USER BROWSER                         │
│                  (React + LiveKit Client SDK)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP: GET /getToken
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      TOKEN SERVER                            │
│                  (FastAPI - Port 8000)                       │
│              Issues JWT tokens for LiveKit                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Returns: {token, url}
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      LIVEKIT CLOUD                           │
│                   (WebRTC/WebSocket SFU)                     │
│              Routes audio streams bidirectionally            │
└───────────┬──────────────────────────────┬──────────────────┘
            │                              │
            │ Audio Stream                 │ Audio Stream
            ↓                              ↑
┌─────────────────────────────────────────────────────────────┐
│                       VOICE AGENT                            │
│           (Python + LiveKit Agents SDK)                      │
│    • Manages conversation with AgentSession                  │
│    • Connects to Gemini Live API                             │
│    • Provides lookup_company_info function tool              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Audio + Function Calls
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
                         │ Function Call: lookup_company_info(query)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                       RAG SYSTEM                             │
│                    (rag.py + FAISS)                          │
│    • Embeds user query with all-MiniLM-L6-v2                │
│    • Searches FAISS vector database (79 embeddings)          │
│    • Returns top-3 relevant Q&A pairs                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Reads FAQ data
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                            │
│                  (data/ecommerce.json)                       │
│    79 FAQ entries about orders, shipping, returns, etc.      │
└─────────────────────────────────────────────────────────────┘
```

---

## Component 1: Voice Agent (LiveKit + Gemini Integration)

### Purpose
The voice agent is a Python worker process that bridges LiveKit's audio infrastructure with Google Gemini Live API, enabling real-time voice conversations.

### Implementation

```python
# agent.py - Core implementation

from livekit.agents import JobContext, AutoSubscribe
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import google
from livekit.agents.llm import function_tool
import rag

async def entrypoint(ctx: JobContext):
    # Step 1: Connect to LiveKit Room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Step 2: Initialize Gemini Live API model
    model = google.beta.realtime.RealtimeModel(
        model="gemini-live-2.5-flash-preview",
        voice="Fenrir",
    )
    
    # Step 3: Define agent with instructions
    agent = Agent(
        instructions=(
            "You are a helpful FAQ assistant. "
            "You ONLY have access to general FAQ information. "
            "Always use the lookup_company_info tool for e-commerce questions."
        ),
    )
    
    # Step 4: Register RAG function tool
    @function_tool
    async def lookup_company_info(query: str):
        """Searches company's FAQ database for information."""
        return rag.search(query)
    
    # Step 5: Start conversation session
    session = AgentSession(llm=model)
    await session.start(agent, room=ctx.room)
```

### Key Characteristics

- **Framework**: LiveKit Agents SDK provides the voice agent lifecycle
- **Model**: Gemini Live API handles audio-to-audio processing natively
- **Connection**: Agent joins LiveKit Room and subscribes to audio tracks
- **Session Management**: `AgentSession` manages the conversation state
- **Function Calling**: Agent can invoke Python functions when Gemini requests them

---

## How LiveKit Connects to Gemini Live API

### Audio Pipeline Flow

```
1. USER SPEAKS
   ↓
2. Browser captures audio via microphone (MediaStream API)
   ↓
3. LiveKit Client SDK encodes audio to Opus codec
   ↓
4. WebSocket transmission to LiveKit Cloud SFU
   ↓
5. LiveKit Cloud routes audio to Voice Agent
   ↓
6. Agent forwards audio stream to Gemini Live API
   ↓
7. Gemini processes audio natively (integrated STT)
   ↓
8. Gemini understands intent and decides actions
   ↓
9. [If needed] Gemini calls lookup_company_info function
   ↓
10. [If called] RAG system retrieves relevant context
   ↓
11. Gemini generates response (with RAG context if applicable)
   ↓
12. Gemini synthesizes speech (integrated TTS)
   ↓
13. Agent receives audio response from Gemini
   ↓
14. Agent publishes audio to LiveKit Room
   ↓
15. LiveKit Cloud routes to browser
   ↓
16. Browser plays audio through speakers
   ↓
17. USER HEARS RESPONSE
```

### Technical Details

**Connection Establishment:**
1. Agent starts and registers with LiveKit Cloud as available worker
2. When user connects, LiveKit creates a job request
3. Agent receives job and joins the specified room
4. Agent subscribes to audio tracks from participants

**Audio Streaming:**
- **Protocol**: WebSocket (WSS) for persistent bidirectional connection
- **Codec**: Opus (WebRTC standard, optimized for voice)
- **Sample Rate**: 24 kHz (Gemini Live API native rate)
- **Bitrate**: 96 kbps (high quality, configurable on client)
- **Latency**: ~200-500ms browser↔LiveKit, ~500-1000ms Gemini processing

**Gemini Integration:**
```python
# Agent uses google.beta.realtime.RealtimeModel
# This provides a unified streaming API that:
# 1. Accepts audio input directly (no separate STT needed)
# 2. Processes language understanding
# 3. Executes function calls when needed
# 4. Outputs audio directly (no separate TTS needed)

model = google.beta.realtime.RealtimeModel(
    model="gemini-live-2.5-flash-preview",
    voice="Fenrir",  # Voice personality for TTS
)
```

**Why This Architecture:**
- **Unified API**: Single model handles STT → LLM → TTS pipeline
- **Low Latency**: Native audio processing eliminates conversion overhead
- **Streaming**: Real-time processing enables natural conversation flow
- **Function Calling**: Built-in support for tool/function execution

---

## Component 2: RAG Integration with Gemini

### Purpose
RAG (Retrieval-Augmented Generation) provides the agent with access to a knowledge base, allowing it to answer questions with accurate, grounded information from the FAQ database.

### Implementation Architecture

```python
# rag.py - Core RAG implementation

from sentence_transformers import SentenceTransformer
import faiss
import json

# Global state (initialized once)
_model = None  # SentenceTransformer model
_index = None  # FAISS vector index
_questions_data = None  # Original FAQ data

def _initialize():
    """Initialize RAG system with embeddings."""
    global _model, _index, _questions_data
    
    # Load embedding model (384-dimensional vectors)
    _model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Load FAQ data
    with open('data/ecommerce.json', 'r') as f:
        data = json.load(f)
        _questions_data = data['questions']
    
    # Check if cached embeddings exist
    if os.path.exists('embeddings_cache/faiss_index.bin'):
        # Load from cache (fast: <1 second)
        _load_index_from_disk()
    else:
        # Generate embeddings (first run: 3-5 seconds)
        _generate_embeddings()
        _save_index_to_disk()

def search(query: str, top_k: int = 3) -> str:
    """
    Search knowledge base for relevant Q&A pairs.
    
    Args:
        query: User's question or keywords
        top_k: Number of results to return
        
    Returns:
        Formatted string with Q&A pairs
    """
    if _model is None:
        _initialize()
    
    # 1. Embed the query
    query_embedding = _model.encode(
        [query], 
        convert_to_numpy=True, 
        normalize_embeddings=True
    )
    
    # 2. Search FAISS index
    distances, indices = _index.search(query_embedding, top_k)
    
    # 3. Format results
    results = []
    for i, idx in enumerate(indices[0]):
        q_data = _questions_data[int(idx)]
        results.append(f"Q: {q_data['question']}\nA: {q_data['answer']}")
    
    return "\n\n".join(results)
```

### RAG-Gemini Integration Flow

**1. Function Tool Registration:**

During agent initialization, the `lookup_company_info` function is registered with Gemini:

```python
@function_tool
async def lookup_company_info(query: str):
    """
    Searches the company's FAQ database for information about orders, 
    shipping, returns, payments, and policies.
    
    Args:
        query: The user's question or keywords to search for
    """
    return rag.search(query, top_k=3)
```

**Key Points:**
- Function signature and docstring sent to Gemini
- Gemini uses docstring to understand when to call this function
- Agent executes the function when Gemini requests it

**2. Conversation Example:**

```
User: "What's your return policy?"
    ↓
Gemini receives audio, transcribes: "What's your return policy?"
    ↓
Gemini analyzes intent: User asking about returns
    ↓
Gemini decides: Need to call lookup_company_info("return policy")
    ↓
Agent executes: lookup_company_info("return policy")
    ↓
RAG System Process:
    1. Embeds query "return policy" → [0.123, -0.456, ..., 0.789] (384-dim)
    2. Searches FAISS index with L2 distance
    3. Finds top-3 similar vectors:
       - Distance: 0.0 (perfect match)
       - Distance: 0.234 (very similar)
       - Distance: 0.456 (similar)
    4. Retrieves corresponding Q&A pairs:
       
       Q: What is your return policy?
       A: You can return items within 30 days of delivery for a full refund...
       
       Q: How do I initiate a return?
       A: Log into your account, go to Orders, click Return Items...
       
       Q: Are there any items that cannot be returned?
       A: Personalized items and opened software cannot be returned...
    ↓
Function returns formatted Q&A text to Gemini
    ↓
Gemini receives context and generates natural response:
"Our return policy allows you to return items within 30 days of delivery 
for a full refund. To start a return, simply log into your account..."
    ↓
Gemini synthesizes response to audio
    ↓
User hears natural, contextually accurate answer
```

**3. Why Function Calling:**

Traditional RAG approaches inject context into every prompt:
```
Prompt: "Context: [FAQ data]. User question: What's your return policy?"
```

Gemini Live API's function calling is superior because:
- ✅ **Selective Retrieval**: Only retrieves when needed (not every query)
- ✅ **Dynamic Context**: Retrieves based on actual question content
- ✅ **Efficient**: Doesn't bloat every prompt with full knowledge base
- ✅ **Native Integration**: Gemini decides when it needs external knowledge
- ✅ **Scalable**: Can add multiple tools/functions for different data sources

---

## Component 3: Vector Search Details

### Embedding Model

**Model**: `sentence-transformers/all-MiniLM-L6-v2`

**Characteristics:**
- **Dimension**: 384-dimensional dense vectors
- **Size**: ~90 MB download
- **Speed**: ~100ms per query embedding (after model load)
- **Quality**: Optimized for semantic similarity tasks
- **Normalization**: Vectors normalized to unit length (magnitude = 1.0)

**Why This Model:**
- Good balance between speed and quality
- Small enough for local deployment
- Pre-trained on large corpus for general semantic understanding
- Fast enough for real-time retrieval (<10ms search)

### FAISS Index

**Index Type**: `IndexFlatL2`

**Characteristics:**
- **Distance Metric**: L2 (Euclidean) distance
- **Search Complexity**: O(n) - exhaustive search (acceptable for 79 documents)
- **Memory**: ~122 KB for 79 vectors × 384 dimensions
- **Accuracy**: Exact nearest neighbor (not approximate)

**Index Structure:**
```
FAISS IndexFlatL2
├── 79 vectors (one per FAQ entry)
├── Each vector: 384 float32 values
├── Distance calculation: √(Σ(q_i - d_i)²)
└── Returns: k nearest neighbors with distances
```

**Why L2 Distance:**
- Since vectors are normalized, L2 distance ≈ cosine distance
- Faster computation than cosine (no division needed)
- Equivalent ranking for normalized vectors

### Retrieval Process

**Step-by-Step:**

1. **Query Embedding**
   ```python
   query = "return policy"
   query_vector = model.encode([query])  # Shape: (1, 384)
   # Normalize to unit length
   query_vector = query_vector / np.linalg.norm(query_vector)
   ```

2. **FAISS Search**
   ```python
   distances, indices = index.search(query_vector, k=3)
   # distances: [0.0, 0.234, 0.456]  # Lower = more similar
   # indices: [42, 17, 8]             # Document IDs
   ```

3. **Result Retrieval**
   ```python
   results = []
   for idx in indices[0]:
       doc = questions_data[idx]
       results.append(f"Q: {doc['question']}\nA: {doc['answer']}")
   ```

4. **Context Formatting**
   ```python
   context = "\n\n".join(results)
   return context  # Sent to Gemini
   ```

**Performance:**
- **First run**: 3-5 seconds (downloads model + generates embeddings)
- **Cached runs**: <1 second (loads from `embeddings_cache/`)
- **Search latency**: <10 milliseconds per query
- **Cache size**: ~170 KB (FAISS index + metadata)

---

## Component 4: WebSocket Communication

### Connection Lifecycle

**1. Initial Connection:**
```
Browser → GET http://localhost:8000/getToken
Token Server → Returns {token: JWT, url: "wss://..."}
Browser → Opens WebSocket to LiveKit Cloud with JWT
LiveKit → Validates token, creates session
LiveKit → Notifies Voice Agent of new participant
Agent → Joins room, subscribes to audio tracks
```

**2. Bidirectional Audio Streaming:**
```
[User speaks]
Browser captures microphone → MediaStream API
LiveKit SDK encodes → Opus frames
WebSocket sends → Binary audio packets
    ↓
LiveKit Cloud receives → Routes to Voice Agent
    ↓
Agent processes → Sends to Gemini
    ↓
[Agent responds]
Gemini generates audio → Agent receives
Agent publishes → LiveKit Room
    ↓
LiveKit Cloud routes → Browser via WebSocket
    ↓
Browser decodes → Plays audio
[User hears]
```

**3. Connection Persistence:**
- WebSocket remains open for entire conversation
- Heartbeat/ping messages maintain connection
- Automatic reconnection on network interruption
- Graceful cleanup on disconnect

### Audio Quality Configuration

**Browser Side (React UI):**
```jsx
<LiveKitRoom
  options={{
    audioCaptureDefaults: {
      echoCancellation: true,    // Remove acoustic echo
      noiseSuppression: true,    // Filter background noise
      autoGainControl: true,     // Normalize volume
    },
    publishDefaults: {
      audioPreset: {
        maxBitrate: 96_000,      // 96 kbps (high quality)
      },
      dtx: false,                // Disable discontinuous transmission
    },
    adaptiveStream: true,        // Adjust quality based on network
    dynacast: true,              // Dynamic broadcast optimization
  }}
/>
```

**Agent Side:**
- Receives high-quality audio from LiveKit
- Forwards to Gemini at 24 kHz sample rate
- Publishes Gemini's response back to LiveKit
- No additional audio processing needed

---

## Security Architecture

### Token-Based Authentication

**Flow:**
1. User initiates connection from browser
2. Browser requests token from Token Server (localhost:8000)
3. Token Server generates JWT with:
   - LiveKit API Key + Secret for signing
   - Room name: "my-room"
   - Participant identity: unique user ID
   - Grants: room_join, can_publish, can_subscribe
   - Expiry: 10 minutes (configurable)
4. Browser receives token + LiveKit URL
5. Browser connects to LiveKit Cloud with JWT
6. LiveKit validates signature and grants access

**Security Features:**
- JWT tokens expire after 10 minutes
- Tokens scoped to specific room
- Cannot be reused for different rooms
- API Secret never exposed to browser
- Token Server can implement additional authorization logic

### API Key Management

**Environment Variables (.env):**
```bash
GOOGLE_API_KEY=AIzaSy...        # Gemini API access
LIVEKIT_API_KEY=APIxxx...       # LiveKit project ID
LIVEKIT_API_SECRET=xxx...       # JWT signing secret
LIVEKIT_URL=wss://...           # LiveKit server URL
```

**Best Practices:**
- Never commit `.env` file to version control
- Rotate keys regularly
- Use separate keys for dev/prod environments
- Restrict API key permissions to minimum required

---

## Performance Characteristics

### Latency Breakdown

| Stage | Latency | Notes |
|-------|---------|-------|
| User speaks → Browser captures | ~20-50ms | Hardware dependent |
| Browser → LiveKit Cloud | ~50-150ms | Network dependent |
| LiveKit → Agent | ~50-100ms | Server location |
| Agent → Gemini | ~100-200ms | API call overhead |
| Gemini processing (STT+LLM) | ~300-800ms | Model inference |
| RAG search (if called) | ~5-10ms | FAISS lookup |
| Gemini TTS generation | ~200-400ms | Audio synthesis |
| Response path (reverse) | ~200-400ms | Same as input path |
| **Total Round-Trip** | **1-2 seconds** | Typical conversation |

### Scalability Considerations

**Current Deployment:**
- Single agent instance
- Handles one conversation at a time
- Suitable for development/testing

**Production Scaling:**
- Deploy multiple agent workers
- LiveKit automatically load balances
- Each agent handles one conversation
- Horizontal scaling based on concurrent users

**Resource Requirements:**
- **RAM**: ~500 MB per agent instance
- **CPU**: Minimal (mostly I/O bound)
- **Network**: ~100 kbps per active conversation
- **Storage**: ~200 MB (models + embeddings)

---

## Summary

This architecture demonstrates a modern approach to building voice AI systems:

1. **LiveKit** provides robust real-time audio infrastructure with WebRTC
2. **Gemini Live API** unifies STT, LLM, and TTS into a single streaming model
3. **FAISS RAG** grounds responses in factual knowledge base data
4. **Function Calling** enables dynamic, selective knowledge retrieval
5. **WebSocket** enables low-latency bidirectional audio streaming
6. **JWT Authentication** ensures secure, scoped access control

The system achieves sub-2-second response times while maintaining high audio quality and accurate, knowledge-grounded responses.
