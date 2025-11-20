import asyncio
import websockets
import json
import pyaudio
import base64
from typing import Optional, Callable
from loguru import logger
from config.settings import settings

class ElevenLabsConversationalAgent:
    """
    ElevenLabs Conversational AI 2.0 - Full duplex voice conversation with interruption support.
    """
    
    def __init__(self, agent_id: Optional[str] = None, api_key: Optional[str] = None):
        self.agent_id = agent_id or settings.ELEVENLABS_AGENT_ID
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.ws_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
        
        # Audio configuration
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        
        # State
        self.websocket = None
        self.audio = pyaudio.PyAudio()
        self.stream_input = None
        self.stream_output = None
        self.is_running = False
        self.audio_buffer = []
        
    async def connect(self):
        """Establish WebSocket connection to ElevenLabs Conversational AI."""
        headers = {
            "xi-api-key": self.api_key
        }
        
        logger.info(f"Connecting to ElevenLabs Conversational AI agent: {self.agent_id}")
        self.websocket = await websockets.connect(
            self.ws_url,
            extra_headers=headers
        )
        logger.info("Connected successfully")
        
    async def send_conversation_initiation_metadata(self, metadata: dict):
        """Send initial conversation metadata."""
        message = {
            "type": "conversation_initiation_client_data",
            "conversation_initiation_client_data": metadata
        }
        await self.websocket.send(json.dumps(message))
        
    async def send_audio_chunk(self, audio_data: bytes):
        """Send user audio chunk to agent."""
        encoded = base64.b64encode(audio_data).decode('utf-8')
        message = {
            "type": "user_audio_chunk",
            "user_audio_chunk": encoded
        }
        await self.websocket.send(json.dumps(message))
        
    async def capture_microphone(self):
        """Capture audio from microphone and send to agent."""
        self.stream_input = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        logger.info("🎤 Microphone active - Start speaking...")
        
        while self.is_running:
            try:
                audio_data = self.stream_input.read(self.chunk_size, exception_on_overflow=False)
                await self.send_audio_chunk(audio_data)
                await asyncio.sleep(0.01)  # Prevent tight loop
            except Exception as e:
                logger.error(f"Microphone capture error: {e}")
                break
                
    async def play_audio(self, audio_data: bytes):
        """Play audio from agent."""
        if self.stream_output is None:
            self.stream_output = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True
            )
        
        self.stream_output.write(audio_data)
        
    async def handle_messages(self):
        """Handle incoming messages from agent."""
        while self.is_running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                event_type = data.get("type")
                
                if event_type == "audio_event":
                    # Agent is speaking
                    audio_event = data.get("audio_event", {})
                    audio_base64 = audio_event.get("audio_base_64")
                    
                    if audio_base64:
                        audio_bytes = base64.b64decode(audio_base64)
                        await self.play_audio(audio_bytes)
                        
                elif event_type == "interruption":
                    # User interrupted agent
                    logger.info("🔇 Interruption detected - Clearing audio buffer")
                    self.audio_buffer.clear()
                    if self.stream_output:
                        # Clear the output stream buffer
                        self.stream_output.stop_stream()
                        self.stream_output.start_stream()
                        
                elif event_type == "agent_response":
                    # Agent finished turn
                    response = data.get("agent_response", {})
                    logger.info(f"Agent: {response}")
                    
                elif event_type == "user_transcript":
                    # User speech transcription
                    transcript = data.get("user_transcript", {})
                    text = transcript.get("text", "")
                    logger.info(f"User: {text}")
                    
                elif event_type == "ping":
                    # Keep-alive ping
                    pong = {"type": "pong", "event_id": data.get("ping", {}).get("event_id")}
                    await self.websocket.send(json.dumps(pong))
                    
                else:
                    logger.debug(f"Received event: {event_type}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                
    async def start_conversation(self, initial_message: Optional[str] = None):
        """Start a conversation with the agent."""
        self.is_running = True
        
        # Initialize conversation
        metadata = {
            "custom_llm_extra_body": {
                "language": "auto-detect"  # Multi-language support
            }
        }
        
        if initial_message:
            metadata["initial_message"] = initial_message
            
        await self.send_conversation_initiation_metadata(metadata)
        
        # Start microphone capture and message handling concurrently
        await asyncio.gather(
            self.capture_microphone(),
            self.handle_messages()
        )
        
    async def stop_conversation(self):
        """Stop the conversation and cleanup resources."""
        logger.info("Stopping conversation...")
        self.is_running = False
        
        if self.stream_input:
            self.stream_input.stop_stream()
            self.stream_input.close()
            
        if self.stream_output:
            self.stream_output.stop_stream()
            self.stream_output.close()
            
        if self.websocket:
            await self.websocket.close()
            
        self.audio.terminate()
        logger.info("Conversation ended")
        
    async def run(self, initial_message: Optional[str] = None):
        """Main entry point to run the conversational agent."""
        try:
            await self.connect()
            await self.start_conversation(initial_message)
        except KeyboardInterrupt:
            logger.info("\n🛑 User interrupted conversation")
        finally:
            await self.stop_conversation()


async def main():
    """Example usage of ElevenLabs Conversational Agent."""
    agent_id = settings.ELEVENLABS_AGENT_ID
    
    agent = ElevenLabsConversationalAgent(agent_id=agent_id)
    
    initial_message = "Hi, I'm having trouble with a Python error. Can you help me debug it?"
    
    await agent.run(initial_message=initial_message)


if __name__ == "__main__":
    logger.info("🎙️ ElevenLabs Conversational AI - DebugGenie Voice Assistant")
    logger.info("Press Ctrl+C to stop")
    asyncio.run(main())
