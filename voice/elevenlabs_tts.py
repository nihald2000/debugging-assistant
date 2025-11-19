import hashlib
import os
from typing import Optional, Dict, Any
from pathlib import Path
import io

from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from cachetools import TTLCache
from loguru import logger

from core.solution_ranker import RankedSolution

class VoiceExplainer:
    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)
        
        # Voice configuration - Rachel (friendly, professional)
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"
        self.voice_settings = VoiceSettings(
            stability=0.75,
            similarity_boost=0.85,
            style=0.5,
            use_speaker_boost=True
        )
        
        # Cache: 50 items, 1 hour TTL
        self.cache = TTLCache(maxsize=50, ttl=3600)
        
        # Cache directory for audio files
        self.cache_dir = Path(".cache/audio")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _format_steps_for_voice(self, steps: list) -> str:
        """Format steps in a natural conversational way."""
        if not steps:
            return "No specific steps required."
        
        formatted = []
        for idx, step in enumerate(steps, 1):
            # Add natural pauses with commas
            formatted.append(f"Step {idx}: {step}.")
        
        return " ".join(formatted)
    
    def _format_script(self, solution: RankedSolution, mode: str = "summary") -> str:
        """
        Format explanation script based on mode.
        
        Args:
            solution: The ranked solution to explain
            mode: 'summary', 'walkthrough', or 'steps'
        """
        if mode == "summary":
            # 30-second quick summary
            script = f"""
            I've identified the issue! {solution.description[:200]}
            
            The confidence level for this solution is {solution.confidence * 100:.0f} percent.
            
            {solution.why_ranked_here}
            """
        
        elif mode == "walkthrough":
            # 1-2 minute detailed walkthrough
            script = f"""
            Let me walk you through this error and its solution.
            
            The problem is: {solution.description}
            
            This solution ranked {self._ordinal(solution.rank)} because {solution.why_ranked_here}
            
            Now, here's how to fix it:
            {self._format_steps_for_voice(solution.steps)}
            
            """
            
            if solution.trade_offs:
                script += f"\nKeep in mind: {'. '.join(solution.trade_offs)}"
            
            script += f"\n\nThe overall confidence for this approach is {solution.confidence * 100:.0f} percent."
        
        else:  # steps mode
            # Detailed step-by-step
            script = f"""
            Here are the step-by-step instructions to fix the issue:
            
            {self._format_steps_for_voice(solution.steps)}
            
            If you need more details, check the visual analysis in the interface.
            """
        
        return script.strip()
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return f"{n}{suffix}"
    
    def generate_explanation(
        self, 
        solution: RankedSolution, 
        mode: str = "summary"
    ) -> Optional[bytes]:
        """
        Generate voice explanation of solution.
        
        Args:
            solution: RankedSolution object
            mode: 'summary', 'walkthrough', or 'steps'
            
        Returns:
            Audio bytes or None if generation fails
        """
        try:
            # Format script
            script = self._format_script(solution, mode)
            
            # Check cache
            cache_key = self._get_cache_key(script)
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            
            if cache_file.exists():
                logger.info(f"Using cached audio for {mode} explanation")
                with open(cache_file, 'rb') as f:
                    return f.read()
            
            logger.info(f"Generating {mode} voice explanation...")
            
            # Generate audio
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=script,
                model_id="eleven_multilingual_v2",
                voice_settings=self.voice_settings
            )
            
            # Collect audio bytes
            audio_bytes = b"".join(audio_generator)
            
            # Cache it
            with open(cache_file, 'wb') as f:
                f.write(audio_bytes)
            
            logger.info("Voice explanation generated successfully")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            return None
    
    def generate_error_summary(self, error_text: str, root_cause: str) -> Optional[bytes]:
        """
        Generate a quick summary of the error.
        
        Args:
            error_text: The error message
            root_cause: Identified root cause
        """
        try:
            script = f"""
            Error detected! Here's a quick summary.
            
            The error is: {error_text[:150]}
            
            The root cause appears to be: {root_cause[:200]}
            
            I'm analyzing this with multiple AI agents to find the best solution.
            """
            
            cache_key = self._get_cache_key(script)
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    return f.read()
            
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=script,
                model_id="eleven_multilingual_v2",
                voice_settings=self.voice_settings
            )
            
            audio_bytes = b"".join(audio_generator)
            
            with open(cache_file, 'wb') as f:
                f.write(audio_bytes)
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error summary generation failed: {e}")
            return None
    
    def save_audio(self, audio_bytes: bytes, filename: str = "explanation.mp3") -> str:
        """
        Save audio bytes to file and return path.
        
        Args:
            audio_bytes: Audio data
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        output_path = self.cache_dir / filename
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        return str(output_path)
