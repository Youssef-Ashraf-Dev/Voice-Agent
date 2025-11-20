import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from livekit import api

# Load environment variables (LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL)
load_dotenv()

app = FastAPI()

# Enable CORS so the React frontend (running on a different port) can call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/getToken")
async def get_token():
    """
    Generates a LiveKit Access Token for a participant.
    """
    # 1. Create the token using your API credentials
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    )
    
    # 2. Define the participant (The User)
    # We give them a random ID so multiple users can join
    participant_identity = "web-user-" + os.urandom(4).hex()
    token.with_identity(participant_identity)
    token.with_name("Human User")
    
    # 3. Grant permissions
    token.with_grants(api.VideoGrants(
        room_join=True,
        room="my-room",  # CRITICAL: This must match the room name in agent.py
        can_publish=True,
        can_subscribe=True,
    ))
    
    # 4. Return the token and the WebSocket URL to the frontend
    return {
        "token": token.to_jwt(),
        "url": os.getenv("LIVEKIT_URL")
    }

if __name__ == "__main__":
    # Run the server on port 8000
    print("Starting Token Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)