# Voice Agent Web UI

## Simple voice interface for the e-commerce voice agent

### Quick Start

#### 1. Start the Token Server
```bash
# In the main project directory
python token_server.py
```
This runs on `http://localhost:8000`

#### 2. Start the Agent
```bash
# In the main project directory
python agent.py dev
```

#### 3. Start the Web UI
```bash
# In the my-voice-app directory
cd my-voice-app
npm run dev
```
This runs on `http://localhost:5173`

#### 4. Use the App
1. Open `http://localhost:5173` in your browser
2. Click "Start Voice Chat"
3. Allow microphone access when prompted
4. Start speaking! The agent will respond with voice

### Features

✅ **Voice Input** - Speak naturally to the agent  
✅ **Voice Output** - Hear the agent's responses  
✅ **Status Indicators** - See when agent is listening/speaking/thinking  
✅ **Simple UI** - Minimal, focused on functionality  

### Troubleshooting

**"Failed to connect" error:**
- Make sure `token_server.py` is running on port 8000
- Check that `.env` has valid LiveKit credentials

**No agent response:**
- Make sure `agent.py dev` is running
- Check that the room name matches ("my-room" by default)

**Can't hear agent:**
- Check browser audio permissions
- Make sure speakers/headphones are working

**Microphone not working:**
- Allow microphone access in browser
- Try Chrome (recommended browser)

