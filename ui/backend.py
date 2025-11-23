from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.models import DebugResult

class DebugBackend(ABC):
    @abstractmethod
    async def analyze(self, context: Dict[str, Any]) -> DebugResult:
        pass

class LocalBackend(DebugBackend):
    def __init__(self):
        from core.orchestrator import DebugOrchestrator
        self.orchestrator = DebugOrchestrator()
        
    async def analyze(self, context: Dict[str, Any]) -> DebugResult:
        return await self.orchestrator.orchestrate_debug(
            error_context=context,
            stream_callback=None
        )
