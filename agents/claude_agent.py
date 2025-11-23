import json
import asyncio
import os
from typing import Any, Dict, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from loguru import logger

from smolagents import CodeAgent, tool, LiteLLMModel, ApiModel, Tool

# Import MCP tools logic (we'll wrap them as smolagents tools)
from mcp_servers.filesystem_mcp import search_in_files, read_file as fs_read_file, get_file_context as fs_get_context

# Define Tools using @tool decorator

@tool
def read_file_tool(file_path: str) -> str:
    """
    Read the full content of a specific file from the codebase.
    
    Args:
        file_path: The absolute or relative path to the file to read.
    """
    try:
        return fs_read_file(file_path)
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def search_codebase_tool(query: str) -> str:
    """
    Search the codebase for specific string patterns or semantic concepts.
    
    Args:
        query: The search query string.
    """
    try:
        # Using the MCP server's search logic
        results = search_in_files(query)
        return str(results)
    except Exception as e:
        return f"Error searching codebase: {str(e)}"

@tool
def get_file_context_tool(file_path: str, line_number: int, context_lines: int = 5) -> str:
    """
    Get a specific range of lines from a file with context.
    
    Args:
        file_path: Path to the file.
        line_number: Target line number.
        context_lines: Number of context lines to include (default 5).
    """
    try:
        return fs_get_context(file_path, line_number, context_lines)
    except Exception as e:
        return f"Error getting context: {str(e)}"

# Example HF Inference Tool
class ImageClassifierTool(Tool):
    name = "image_classifier"
    description = "Classify an image using a HuggingFace model."
    inputs = {"image_path": {"type": "string", "description": "Path to image file"}}
    output_type = "string"

    def __init__(self):
        self.model = ApiModel("google/vit-base-patch16-224")
        super().__init__()

    def forward(self, image_path: str) -> str:
        # In a real scenario, we'd load the image and send to model
        # For now, we simulate or use the model if inputs allow
        return "Image classification result (simulated)"

class CodebaseAnalysis(BaseModel):
    similar_patterns: List[dict] = Field(description="List of similar code patterns or errors found")
    root_cause_hypothesis: str = Field(description="Hypothesis for the root cause of the issue")
    affected_files: List[str] = Field(description="List of files likely involved in the error")
    dependency_chain: List[str] = Field(description="Chain of dependencies leading to the error")
    code_snippets: List[dict] = Field(description="Relevant code snippets supporting the hypothesis")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")

class ClaudeAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "anthropic/claude-3-5-sonnet-20240620", mcp_client: Any = None): 
        super().__init__(api_key, model)
        self.mcp_client = mcp_client
        
        # Initialize Model
        # Using LiteLLMModel to access Claude via Anthropic API
        self.model_engine = LiteLLMModel(
            model_id=model,
            api_key=api_key
        )
        
        # Collect Tools
        self.agent_tools = [read_file_tool, search_codebase_tool, get_file_context_tool]
        
        # Add HF Inference Tool (as requested)
        # self.agent_tools.append(ImageClassifierTool())
        
        # Initialize smolagents CodeAgent
        # CodeAgent generates Python code to solve tasks, which is great for debugging
        self.agent = CodeAgent(
            tools=self.agent_tools,
            model=self.model_engine,
            additional_authorized_imports=["json", "os", "re"],
            add_base_tools=True # Adds python interpreter, etc.
        )

    def format_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format the system prompt and user message.
        """
        error_info = context.get("error_info", "No specific error provided.")
        visual_analysis = context.get("visual_analysis", {})
        
        prompt = f"""
        You are an expert Codebase Analysis Agent.
        
        Error Information:
        {error_info}
        
        Visual Analysis Findings:
        {json.dumps(visual_analysis, indent=2)}
        
        Task:
        1. Explore the codebase using the available tools.
        2. Search for the error message or relevant code patterns.
        3. Trace the execution flow.
        4. Formulate a hypothesis about the root cause.
        
        Finally, return a JSON object matching this structure:
        {{
            "similar_patterns": [{{"pattern": "str", "location": "str"}}],
            "root_cause_hypothesis": "str",
            "affected_files": ["str"],
            "dependency_chain": ["str"],
            "code_snippets": [{{"file": "str", "code": "str"}}],
            "confidence_score": float
        }}
        """
        return prompt

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deep codebase analysis using smolagents.
        """
        try:
            prompt = self.format_prompt(context)
            
            logger.info("Starting smolagents CodeAgent run...")
            
            # Run agent (CodeAgent.run is synchronous, so we wrap it)
            # The agent will write and execute python code to call tools and solve the task
            response_text = await asyncio.to_thread(self.agent.run, prompt)
            
            # Parse result (CodeAgent returns the final answer as string/object)
            # We expect JSON string based on prompt
            if isinstance(response_text, str):
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError:
                    # If not JSON, wrap it
                    data = {
                        "root_cause_hypothesis": response_text,
                        "confidence_score": 0.5,
                        "similar_patterns": [],
                        "affected_files": [],
                        "dependency_chain": [],
                        "code_snippets": []
                    }
            else:
                # If it returns an object (unlikely for this prompt but possible)
                data = {
                    "root_cause_hypothesis": str(response_text),
                    "confidence_score": 0.5,
                    "similar_patterns": [],
                    "affected_files": [],
                    "dependency_chain": [],
                    "code_snippets": []
                }

            analysis = CodebaseAnalysis(**data)
            return analysis.model_dump()
            
        except Exception as e:
            logger.error(f"Claude (smolagents) analysis failed: {e}")
            return {
                "similar_patterns": [],
                "root_cause_hypothesis": f"Analysis failed: {str(e)}",
                "affected_files": [],
                "dependency_chain": [],
                "code_snippets": [],
                "confidence_score": 0.0
            }
    async def _call_provider(self, prompt: str) -> str:
        """
        Call smolagents CodeAgent synchronously in a thread pool.
        Converts the response to a string format matching BaseAgent interface.
        """
        try:
            logger.info(f"Starting ClaudeAgent (smolagents) run for prompt: {prompt[:50]}...")
            
            # Run agent (CodeAgent.run is synchronous, so we wrap it)
            # The agent will write and execute python code to call tools and solve the task
            response = await asyncio.to_thread(self.agent.run, prompt)
            
            # Handle non-string responses (though CodeAgent usually returns string or object with __str__)
            if not isinstance(response, str):
                response = str(response)
                
            logger.info("ClaudeAgent run completed successfully.")
            return response
            
        except Exception as e:
            logger.error(f"ClaudeAgent run failed: {e}")
            # Return a structured error message that the UI can display
            return f"Error executing agent: {str(e)}"

    async def _stream_provider(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Simulate streaming by chunking the CodeAgent response.
        Note: smolagents doesn't support native streaming yet.
        """
        try:
            # Get full response first
            full_response = await self._call_provider(prompt)
            
            # Split into chunks (sentences or fixed size) to simulate streaming
            # This provides better UX than waiting for the whole block
            chunk_size = 50
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i + chunk_size]
                yield chunk
                # Small delay to simulate generation speed
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"ClaudeAgent stream failed: {e}")
            yield f"Error streaming agent response: {str(e)}"
