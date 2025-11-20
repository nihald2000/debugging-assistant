from typing import Dict, Any, List, Optional
import json
import os
from swarm import Swarm, Agent
from .base_agent import BaseAgent
from loguru import logger
from mcp_servers.web_search_mcp import search_web, search_stack_overflow, get_page_content
from mcp_servers.filesystem_mcp import read_file, list_files

# --- Handoff Functions ---

def transfer_to_visual():
    """Transfer to the Visual Agent for image analysis."""
    return visual_agent

def transfer_to_code():
    """Transfer to the Code Agent for codebase search."""
    return code_agent

def transfer_to_web():
    """Transfer to the Web Agent for online research."""
    return web_agent

def transfer_to_synthesis():
    """Transfer to the Synthesis Agent to combine findings."""
    return synthesis_agent

def transfer_back_to_triage():
    """Transfer back to the Triage Agent for further coordination."""
    return triage_agent

# --- Tool Wrappers ---

def search_web_tool(query: str) -> str:
    """Search the web for information."""
    results = search_web(query)
    return json.dumps(results)

def search_stackoverflow_tool(query: str) -> str:
    """Search Stack Overflow for errors."""
    results = search_stack_overflow(query)
    return json.dumps(results)

def read_file_tool(file_path: str) -> str:
    """Read a file from the codebase."""
    return read_file(file_path)

def list_files_tool(directory: str = ".", pattern: str = "*") -> str:
    """List files in the codebase."""
    results = list_files(directory, pattern)
    return json.dumps(results)

# --- Agent Definitions ---

triage_agent = Agent(
    name="TriageAgent",
    instructions="""You are the Triage Agent.
    Your goal is to orchestrate the debugging process.
    1. Analyze the error context and history.
    2. Decide which specialist to call next:
       - If there is an image/screenshot, call VisualAgent.
       - If you need to check the code, call CodeAgent.
       - If you need external info, call WebAgent.
    3. If you have gathered enough information from specialists, call SynthesisAgent to finalize the report.
    
    Always check the conversation history to see what has already been done.
    """,
    functions=[transfer_to_visual, transfer_to_code, transfer_to_web, transfer_to_synthesis]
)

visual_agent = Agent(
    name="VisualAgent",
    instructions="""You are the Visual Agent.
    Analyze the visual context (screenshots, UI descriptions) provided in the context variables.
    Identify UI elements, error messages, or visual anomalies.
    Once done, transfer back to TriageAgent.
    """,
    functions=[transfer_back_to_triage]
)

code_agent = Agent(
    name="CodeAgent",
    instructions="""You are the Code Agent.
    Search the codebase for error messages, function names, or relevant logic.
    Use `list_files` and `read_file` to explore.
    Once you have found relevant code or need new direction, transfer back to TriageAgent.
    """,
    functions=[read_file_tool, list_files_tool, transfer_back_to_triage]
)

web_agent = Agent(
    name="WebAgent",
    instructions="""You are the Web Agent.
    Search online for similar bugs, documentation, or solutions.
    Use `search_web` and `search_stackoverflow`.
    Once you have gathered info, transfer back to TriageAgent.
    """,
    functions=[search_web_tool, search_stackoverflow_tool, transfer_back_to_triage]
)

synthesis_agent = Agent(
    name="SynthesisAgent",
    instructions="""You are the Synthesis Agent.
    Your goal is to combine all findings from the conversation history into a final report.
    1. Summarize the Root Cause.
    2. Propose Solutions.
    3. Provide Fix Instructions.
    
    Output the final report clearly. This ends the session.
    """,
    functions=[] # No handoffs, this is the end
)

# --- Main Class ---

class OpenAIAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)
        self.client = Swarm() 
        
    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the Swarm of agents to analyze the error.
        """
        logger.info("Starting OpenAI Swarm analysis (Triage Pattern)...")
        
        # Prepare context variables
        swarm_context = {
            "error_text": context.get("error_text", ""),
            "image_description": context.get("image_description", "No image provided"),
            "project_root": os.getcwd()
        }
        
        messages = [
            {"role": "user", "content": f"Please debug this error: {context.get('error_text')}"}
        ]
        
        try:
            # Run the swarm starting with TriageAgent
            response = self.client.run(
                agent=triage_agent,
                messages=messages,
                context_variables=swarm_context,
                max_turns=30
            )
            
            logger.info(f"Swarm finished. Last agent: {response.agent.name}")
            
            final_content = response.messages[-1]["content"]
            
            return {
                "swarm_analysis": final_content,
                "agent_trace": [m["role"] + " (" + (m.get("sender") or "User") + "): " + (m.get("content") or "") for m in response.messages],
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Swarm analysis failed: {e}")
            return {"error": str(e), "status": "failed"}

    def get_metrics(self) -> Dict[str, Any]:
        return {"type": "swarm", "model": self.model}
