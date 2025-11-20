import asyncio
import base64
import os
import sys
import traceback
from typing import Optional

try:
    import cv2
    import pyaudio
    from google import genai
    from google.genai import types
    import numpy as np
    from PIL import Image
except ImportError as e:
    print(f"Missing dependencies for Live API: {e}")
    print("Please install: google-genai pyaudio opencv-python pillow numpy")
    # We don't exit here to allow the file to be imported without crashing, 
    # but the class won't work.

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class GeminiLiveDebugger:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        
        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1alpha"})
        self.model = model
        self.audio_queue = asyncio.Queue()
        self.running = False

    async def start_session(self):
        """Start the multimodal live debugging session."""
        self.running = True
        logger.info("Starting Gemini Live Debugging Session...")
        
        # Audio setup
        self.p = pyaudio.PyAudio()
        # Input stream (Microphone)
        self.input_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        # Output stream (Speaker)
        self.output_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000, # Gemini output rate
            output=True
        )

        config = {"response_modalities": ["AUDIO", "TEXT"]}
        
        async with self.client.aio.live.connect(model=self.model, config=config) as session:
            logger.info("Connected to Gemini Live API")
            
            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self._send_audio_loop(session)),
                asyncio.create_task(self._send_video_loop(session)),
                asyncio.create_task(self._receive_loop(session)),
                asyncio.create_task(self._input_audio_loop())
            ]
            
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Session error: {e}")
            finally:
                self.cleanup()

    async def _input_audio_loop(self):
        """Capture microphone audio and put into queue."""
        while self.running:
            try:
                data = await asyncio.to_thread(self.input_stream.read, 1024, exception_on_overflow=False)
                await self.audio_queue.put(data)
            except Exception as e:
                logger.error(f"Audio capture error: {e}")
                await asyncio.sleep(0.1)

    async def _send_audio_loop(self, session):
        """Send audio chunks to Gemini."""
        while self.running:
            chunk = await self.audio_queue.get()
            await session.send(input={"data": chunk, "mime_type": "audio/pcm"}, end_of_turn=False)

    async def _send_video_loop(self, session):
        """Capture screen/webcam and send frames to Gemini."""
        # Using webcam 0 for demo, or could use screen capture
        cap = cv2.VideoCapture(0) 
        
        logger.info("Started video capture (Webcam)")
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue
            
            # Resize for bandwidth
            frame = cv2.resize(frame, (640, 480))
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            # Send frame (approx 1 FPS or on change)
            await session.send(input={"data": jpg_as_text, "mime_type": "image/jpeg"}, end_of_turn=False)
            
            await asyncio.sleep(1.0) # 1 FPS
        
        cap.release()

    async def _receive_loop(self, session):
        """Receive responses from Gemini."""
        async for response in session.receive():
            if response.server_content is None:
                continue

            model_turn = response.server_content.model_turn
            if model_turn is not None:
                for part in model_turn.parts:
                    # Handle Audio
                    if part.inline_data:
                        audio_data = part.inline_data.data
                        # Play audio
                        await asyncio.to_thread(self.output_stream.write, audio_data)
                    
                    # Handle Text
                    if part.text:
                        print(f"Gemini: {part.text}", end="", flush=True)

            if response.server_content.turn_complete:
                print("\n")

    def cleanup(self):
        self.running = False
        if hasattr(self, 'input_stream'): self.input_stream.close()
        if hasattr(self, 'output_stream'): self.output_stream.close()
        if hasattr(self, 'p'): self.p.terminate()
        logger.info("Session cleanup complete")

if __name__ == "__main__":
    # Example usage
    debugger = GeminiLiveDebugger()
    try:
        asyncio.run(debugger.start_session())
    except KeyboardInterrupt:
        print("Stopping session...")
        debugger.cleanup()
