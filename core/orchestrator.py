import asyncio
import json
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from loguru import logger
from pydantic import BaseModel, Field

from agents.gemini_agent import GeminiAgent
from agents.claude_agent import ClaudeAgent
from agents.openai_agent import OpenAIAgent
from config.api_keys import api_config

from core.models import DebugResult

from core.mcp_client import MCPClientManager
from pathlib import Path

class DebugOrchestrator:
    def __init__(self):
        self.gemini_agent = GeminiAgent(api_key=api_config.google_ai_api_key)
        self.claude_agent = ClaudeAgent(api_key=api_config.anthropic_api_key)
        self.openai_agent = OpenAIAgent(api_key=api_config.openai_api_key)
        
        # For synthesis, we reuse the Claude agent instance but with a different prompt
        self.synthesizer = self.claude_agent
        
        # MCP Client
        self.mcp_client = MCPClientManager()
        self.mcp_initialized = False

    async def startup(self):
        """Initialize MCP connections."""
        if self.mcp_initialized:
            return

        try:
            config_path = Path("claude_desktop_config.json")
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                servers = config.get("mcpServers", {})
                for name, server_config in servers.items():
                    cmd = server_config.get("command")
                    args = server_config.get("args", [])
                    env = server_config.get("env", {})
                    
                    if cmd:
                        await self.mcp_client.connect_stdio(name, cmd, args, env)
            
            # Update agents with MCP capabilities
            # We inject the client into ClaudeAgent so it can use the tools
            self.claude_agent.mcp_client = self.mcp_client
            if self.mcp_client.tools:
                self.claude_agent.tools = self.mcp_client.tools
                logger.info(f"Updated ClaudeAgent with {len(self.mcp_client.tools)} MCP tools")
                
            self.mcp_initialized = True
            
        except Exception as e:
            logger.error(f"MCP startup failed: {e}")

    async def parse_error(self, error_text: str) -> Dict[str, Any]:
        """
        Basic parsing of error text to extract key components.
        In a real system, this might use an LLM or regex.
        """
        return {
            "raw_text": error_text,
            "summary": error_text[:200] if error_text else "No error text provided"
        }

    async def _run_agent_safe(self, agent_task, name: str) -> Any:
        """Wrapper to handle agent failures gracefully."""
        try:
            return await agent_task
        except Exception as e:
            logger.error(f"Agent {name} failed: {e}")
            return {"error": str(e), "status": "failed"}

    async def synthesize_results(self, visual_analysis: Any, codebase_analysis: Any, web_research: Any) -> Dict[str, Any]:
        """Use Claude to synthesize multi-agent findings."""
        
        synthesis_prompt = f"""
        You are the Lead Debugging Architect. Your goal is to synthesize findings from three specialized AI agents into a coherent debugging report.
        
        --- AGENT FINDINGS ---
        
        1. VISUAL ANALYSIS (Gemini):
        {json.dumps(visual_analysis if not isinstance(visual_analysis, Exception) else str(visual_analysis), indent=2, default=str)}
        
        2. CODEBASE ANALYSIS (Claude):
        {json.dumps(codebase_analysis if not isinstance(codebase_analysis, Exception) else str(codebase_analysis), indent=2, default=str)}
        
        3. WEB RESEARCH (OpenAI):
        {json.dumps(web_research if not isinstance(web_research, Exception) else str(web_research), indent=2, default=str)}
        
        --- INSTRUCTIONS ---
        
        Based on the above, provide a final report containing:
        1. ROOT CAUSE: A definitive explanation of why the error occurred. Resolve any contradictions between agents.
        2. SOLUTIONS: Top 3 ranked solutions. For each, provide a title, description, and estimated success probability.
        3. FIX INSTRUCTIONS: Step-by-step instructions to apply the best solution.
        4. CONFIDENCE: An overall confidence score (0.0 to 1.0).
        
        Output strictly as valid JSON matching this structure:
        {{
            "root_cause": "string",
            "solutions": [
                {{"title": "string", "description": "string", "probability": float}}
            ],
            "fix_instructions": "string",
            "confidence_score": float
        }}
        """
        
        try:
            response = await self.synthesizer.call_llm(synthesis_prompt)
            
            # Clean JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            return json.loads(response)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "root_cause": "Synthesis failed. Please review individual agent outputs.",
                "solutions": [],
                "fix_instructions": "Check agent logs.",
                "confidence_score": 0.0
            }

    async def orchestrate_debug(self, error_context: Dict[str, Any], stream_callback=None) -> DebugResult:
        """
        Run all agents in parallel and synthesize results.
        
        Args:
            error_context: Dict containing 'error_text', 'image' (optional), 'code_context' (optional).
            stream_callback: Optional async function to report progress.
        """
        start_time = time.time()
        logger.info("Starting debug orchestration...")
        
        # Initialize MCP
        await self.startup()
        
        if stream_callback:
            await stream_callback("Starting analysis...")

        # 1. Parse Error (Fast)
        parsed_error = await self.parse_error(error_context.get('error_text', ''))
        error_context['parsed_error'] = parsed_error
        
        # 2. Define Tasks
        tasks = []
        task_names = []
        
        # Always run Web Research
        tasks.append(self._run_agent_safe(self.openai_agent.analyze(error_context), "OpenAI"))
        task_names.append("web_research")
        
        # Run Visual Analysis if image is present
        if error_context.get('image'):
            tasks.append(self._run_agent_safe(self.gemini_agent.analyze(error_context), "Gemini"))
            task_names.append("visual_analysis")
        else:
            # Placeholder if no image
            async def no_op(): return {"status": "skipped", "reason": "No image provided"}
            tasks.append(no_op())
            task_names.append("visual_analysis")
            
        # Run Codebase Analysis
        # We might want to wait for visual analysis to feed into codebase analysis, 
        # but for speed we'll run them in parallel and let Claude use the raw error text first.
        # Refinement: If we wanted sequential, we'd await gemini first. 
        # For now, parallel is requested.
        tasks.append(self._run_agent_safe(self.claude_agent.analyze(error_context), "Claude"))
        task_names.append("codebase_analysis")
        
        if stream_callback:
            await stream_callback("Running agents in parallel...")

        # 3. Execute Parallel
        results_list = await asyncio.gather(*tasks)
        
        # Map results back to names
        results = dict(zip(task_names, results_list))
        
        if stream_callback:
            await stream_callback("Synthesizing findings...")

        # 4. Synthesize
        synthesis = await self.synthesize_results(
            results["visual_analysis"],
            results["codebase_analysis"],
            results["web_research"]
        )
        
        execution_time = time.time() - start_time
        
        # 5. Collect Metrics
        metrics = {
            "gemini": self.gemini_agent.get_metrics(),
            "claude": self.claude_agent.get_metrics(),
            "openai": self.openai_agent.get_metrics()
        }
        
        final_result = DebugResult(
            root_cause=synthesis.get("root_cause", "Unknown"),
            solutions=synthesis.get("solutions", []),
            fix_instructions=synthesis.get("fix_instructions", ""),
            confidence_score=synthesis.get("confidence_score", 0.0),
            agent_metrics=metrics,
            execution_time=execution_time
        )
        
        logger.info(f"Orchestration complete in {execution_time:.2f}s")
        return final_result
