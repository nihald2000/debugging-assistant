import json
from typing import Any, Dict, List, Optional, AsyncGenerator
import anthropic
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

# Import MCP tools directly for now (in a real app, these might be injected or discovered)
from mcp_servers.filesystem_mcp import search_in_files, read_file, get_file_context

class CodebaseAnalysis(BaseModel):
    similar_patterns: List[dict] = Field(description="List of similar code patterns or errors found")
    root_cause_hypothesis: str = Field(description="Hypothesis for the root cause of the issue")
    affected_files: List[str] = Field(description="List of files likely involved in the error")
    dependency_chain: List[str] = Field(description="Chain of dependencies leading to the error")
    code_snippets: List[dict] = Field(description="Relevant code snippets supporting the hypothesis")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")

class ClaudeAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"): # Using available model name
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        
        # Define tools available to Claude
        self.tools = [
            {
                "name": "search_codebase",
                "description": "Search the codebase for specific string patterns or semantic concepts.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "file_types": {"type": "array", "items": {"type": "string"}, "description": "Optional file extensions to filter"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_file",
                "description": "Read the full content of a specific file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Absolute or relative path to the file"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "get_file_context",
                "description": "Get a specific range of lines from a file with context.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"},
                        "line_number": {"type": "integer", "description": "Target line number"},
                        "context_lines": {"type": "integer", "description": "Number of context lines (default 5)"}
                    },
                    "required": ["file_path", "line_number"]
                }
            }
        ]

    def format_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format the system prompt and user message.
        """
        error_info = context.get("error_info", "No specific error provided.")
        visual_analysis = context.get("visual_analysis", {})
        
        prompt = f"""
        You are an expert Codebase Analysis Agent. Your goal is to analyze the provided error and codebase to find the root cause.
        
        Error Information:
        {error_info}
        
        Visual Analysis Findings (if any):
        {json.dumps(visual_analysis, indent=2)}
        
        Task:
        1. Use the available tools to explore the codebase.
        2. Search for the error message or relevant code patterns.
        3. Trace the execution flow and dependencies.
        4. Formulate a hypothesis about the root cause.
        5. Return a structured analysis.
        
        You have access to tools: search_codebase, read_file, get_file_context.
        Use them wisely to gather information before forming your final conclusion.
        """
        return prompt

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute local MCP tools."""
        try:
            logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
            if tool_name == "search_codebase":
                return search_in_files(tool_input["query"], tool_input.get("file_types"))
            elif tool_name == "read_file":
                return read_file(tool_input["file_path"])
            elif tool_name == "get_file_context":
                return get_file_context(
                    tool_input["file_path"], 
                    tool_input["line_number"], 
                    tool_input.get("context_lines", 5)
                )
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _call_provider(self, prompt: str) -> str:
        """
        Call Claude with tool use loop.
        """
        messages = [{"role": "user", "content": prompt}]
        
        # Max turns for tool use to prevent infinite loops
        max_turns = 5
        current_turn = 0
        
        while current_turn < max_turns:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                tools=self.tools,
                messages=messages
            )
            
            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Append assistant's tool use request to history
                messages.append({"role": "assistant", "content": response.content})
                
                # Process all tool blocks
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)
                        })
                
                # Append tool results to history
                messages.append({"role": "user", "content": tool_results})
                current_turn += 1
            else:
                # Final response
                return response.content[0].text

        return "Analysis incomplete: Max tool turns reached."

    async def _stream_provider(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Streaming implementation (simplified, no tool use loop for now).
        """
        async with self.client.messages.stream(
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deep codebase analysis.
        """
        try:
            prompt = self.format_prompt(context)
            
            # We want the final output to be JSON, so we append an instruction
            json_instruction = """
            
            Finally, output your analysis as a valid JSON object matching this structure:
            {
                "similar_patterns": [{"pattern": "str", "location": "str"}],
                "root_cause_hypothesis": "str",
                "affected_files": ["str"],
                "dependency_chain": ["str"],
                "code_snippets": [{"file": "str", "code": "str"}],
                "confidence_score": float
            }
            """
            
            response_text = await self.call_llm(prompt + json_instruction)
            
            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(response_text)
            analysis = CodebaseAnalysis(**data)
            
            return analysis.model_dump()
            
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {
                "similar_patterns": [],
                "root_cause_hypothesis": f"Analysis failed: {str(e)}",
                "affected_files": [],
                "dependency_chain": [],
                "code_snippets": [],
                "confidence_score": 0.0
            }
