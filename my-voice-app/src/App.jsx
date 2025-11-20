import { useState, useEffect } from 'react'
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, useRoomContext } from '@livekit/components-react'
import '@livekit/components-styles'
import './App.css'

function VoiceAssistant() {
  const { state, audioTrack } = useVoiceAssistant()
  const room = useRoomContext()
  
  // Optimize audio playback on mount
  useEffect(() => {
    if (room) {
      // Set audio output device and ensure proper playback
      room.remoteParticipants.forEach(participant => {
        participant.audioTracks.forEach(publication => {
          if (publication.track) {
            const audioElement = publication.track.attach()
            // Ensure smooth playback with optimized settings
            audioElement.autoplay = true
            audioElement.playsInline = true
            // Reduce jitter buffer for lower latency
            if (audioElement.setSinkId) {
              audioElement.setSinkId('default').catch(err => 
                console.log('Could not set audio output device:', err)
              )
            }
          }
        })
      })
      
      // Listen for new participants joining
      room.on('participantConnected', (participant) => {
        participant.on('trackSubscribed', (track) => {
          if (track.kind === 'audio') {
            const audioElement = track.attach()
            audioElement.autoplay = true
            audioElement.playsInline = true
          }
        })
      })
    }
  }, [room])
  
  const getStatusConfig = () => {
    switch(state) {
      case 'speaking':
        return { emoji: '🗣️', text: 'Agent Speaking', color: '#4CAF50', pulse: true }
      case 'listening':
        return { emoji: '👂', text: 'Listening to you', color: '#2196F3', pulse: true }
      case 'thinking':
        return { emoji: '🤔', text: 'Processing', color: '#FF9800', pulse: false }
      case 'idle':
        return { emoji: '💬', text: 'Ready to chat', color: '#9E9E9E', pulse: false }
      default:
        return { emoji: '🔄', text: 'Connecting', color: '#9E9E9E', pulse: false }
    }
  }
  
  const status = getStatusConfig()
  
  return (
    <div style={{ 
      textAlign: 'center', 
      padding: '40px 20px',
      maxWidth: '600px',
      margin: '0 auto'
    }}>
      {/* Status Card */}
      <div style={{
        padding: '40px',
        margin: '30px auto',
        borderRadius: '20px',
        backgroundColor: 'white',
        boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
        transition: 'all 0.3s ease'
      }}>
        {/* Emoji with pulse animation */}
        <div style={{
          fontSize: '4rem',
          marginBottom: '20px',
          animation: status.pulse ? 'pulse 1.5s infinite' : 'none'
        }}>
          {status.emoji}
        </div>
        
        {/* Status text */}
        <div style={{
          fontSize: '1.8rem',
          fontWeight: '600',
          color: status.color,
          marginBottom: '10px',
          transition: 'color 0.3s ease'
        }}>
          {status.text}
        </div>
        
        {/* Status indicator dot */}
        <div style={{
          display: 'inline-block',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: status.color,
          animation: status.pulse ? 'blink 1s infinite' : 'none',
          marginTop: '10px'
        }} />
      </div>
      
      {/* Helper text */}
      <div style={{ 
        padding: '20px',
        backgroundColor: '#f8f9fa',
        borderRadius: '12px',
        border: '2px dashed #e0e0e0',
        marginTop: '30px'
      }}>
        <p style={{ 
          color: '#555', 
          fontSize: '1.1rem',
          margin: 0,
          lineHeight: '1.6'
        }}>
          <span style={{ fontSize: '1.5rem' }}>💡</span>
          <br />
          <strong>Just start speaking!</strong>
          <br />
          <span style={{ fontSize: '0.95rem', color: '#777' }}>
            Ask about orders, shipping, returns, payments, and more
          </span>
        </p>
      </div>

      {audioTrack && <RoomAudioRenderer />}
      
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}

function App() {
  const [token, setToken] = useState(null)
  const [url, setUrl] = useState(null)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState(null)

  const connectToRoom = async () => {
    setConnecting(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/getToken')
      const data = await response.json()
      
      setToken(data.token)
      setUrl(data.url)
    } catch (err) {
      setError('Failed to connect. Make sure token_server.py is running!')
      setConnecting(false)
    }
  }

  const disconnect = () => {
    setToken(null)
    setUrl(null)
  }

  if (error) {
    return (
      <div style={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '24px',
          padding: '50px 40px',
          maxWidth: '500px',
          textAlign: 'center',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
        }}>
          <div style={{ fontSize: '4rem', marginBottom: '20px' }}>❌</div>
          <h1 style={{ color: '#f5576c', marginBottom: '15px' }}>Connection Error</h1>
          <p style={{ color: '#666', fontSize: '1.1rem', marginBottom: '30px' }}>{error}</p>
          <button onClick={connectToRoom} style={{
            padding: '15px 40px',
            fontSize: '1.1rem',
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '50px',
            cursor: 'pointer',
            fontWeight: '600',
            boxShadow: '0 8px 20px rgba(245, 87, 108, 0.4)',
            transition: 'all 0.3s ease'
          }}>
            🔄 Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!token) {
    return (
      <div style={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '24px',
          padding: '50px 40px',
          maxWidth: '600px',
          width: '100%',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🤖</div>
          <h1 style={{ 
            fontSize: '2.5rem', 
            margin: '0 0 15px 0',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: '700'
          }}>
            E-Commerce Voice Agent
          </h1>
          <p style={{ 
            fontSize: '1.2rem', 
            color: '#666', 
            marginBottom: '40px',
            lineHeight: '1.6'
          }}>
            Talk to our AI assistant about orders, shipping, returns, and more!
          </p>
          
          <button 
            onClick={connectToRoom} 
            disabled={connecting}
            style={{
              padding: '18px 50px',
              fontSize: '1.3rem',
              background: connecting 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '50px',
              cursor: connecting ? 'wait' : 'pointer',
              fontWeight: '600',
              boxShadow: '0 8px 20px rgba(102, 126, 234, 0.4)',
              transition: 'all 0.3s ease',
              transform: 'scale(1)',
              opacity: connecting ? 0.7 : 1
            }}
            onMouseEnter={(e) => {
              if (!connecting) {
                e.target.style.transform = 'scale(1.05)'
                e.target.style.boxShadow = '0 12px 28px rgba(102, 126, 234, 0.5)'
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)'
              e.target.style.boxShadow = '0 8px 20px rgba(102, 126, 234, 0.4)'
            }}
          >
            {connecting ? '🔄 Connecting...' : '🎙️ Start Voice Chat'}
          </button>

          <div style={{ 
            marginTop: '40px', 
            textAlign: 'left',
            backgroundColor: '#f8f9fa',
            padding: '25px',
            borderRadius: '16px',
            border: '2px solid #e9ecef'
          }}>
            <h3 style={{ margin: '0 0 15px 0', color: '#333', fontSize: '1.1rem' }}>
              📋 Quick Setup:
            </h3>
            <ol style={{ 
              color: '#555', 
              lineHeight: '2',
              paddingLeft: '20px',
              margin: 0,
              fontSize: '0.95rem'
            }}>
              <li>Ensure <code style={{ 
                backgroundColor: '#fff', 
                padding: '2px 8px', 
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}>token_server.py</code> is running</li>
              <li>Ensure <code style={{ 
                backgroundColor: '#fff', 
                padding: '2px 8px', 
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}>agent.py dev</code> is running</li>
              <li>Click "Start Voice Chat"</li>
              <li>Allow microphone access</li>
            </ol>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f7fa' }}>
      <div style={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '25px 30px', 
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: '600' }}>
            🤖 E-Commerce Voice Agent
          </h1>
          <p style={{ margin: '5px 0 0 0', fontSize: '0.95rem', opacity: 0.9 }}>
            AI-powered customer support
          </p>
        </div>
        <button 
          onClick={disconnect}
          style={{
            padding: '12px 28px',
            backgroundColor: 'rgba(255, 255, 255, 0.2)',
            color: 'white',
            border: '2px solid white',
            borderRadius: '25px',
            cursor: 'pointer',
            fontWeight: '600',
            fontSize: '1rem',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.3)'
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'
          }}
        >
          ← Disconnect
        </button>
      </div>

      <LiveKitRoom
        token={token}
        serverUrl={url}
        connect={true}
        audio={true}
        video={false}
        options={{
          // Audio quality settings for better voice clarity
          audioCaptureDefaults: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          publishDefaults: {
            audioPreset: {
              maxBitrate: 96_000, // Higher bitrate for better quality
            },
            dtx: false, // Disable discontinuous transmission to prevent cutting
          },
          // Adaptive streaming for stable connection
          adaptiveStream: true,
          dynacast: true,
        }}
        style={{ height: 'calc(100vh - 120px)', paddingTop: '20px' }}
      >
        <VoiceAssistant />
      </LiveKitRoom>
    </div>
  )
}

export default App
