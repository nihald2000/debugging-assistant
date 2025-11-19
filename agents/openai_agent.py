import json
from typing import Any, Dict, List, Optional, AsyncGenerator
import openai
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

# Import MCP tools
from mcp_servers.web_search_mcp import search_stack_overflow, search_web, get_page_content, extract_code_snippets
from mcp_servers.github_mcp import search_issues, find_similar_bugs

class WebResearch(BaseModel):
    stack_overflow_solutions: List[dict] = Field(description="Relevant Stack Overflow threads with solutions")
    documentation_links: List[str] = Field(description="Links to relevant official documentation")
    github_solutions: List[dict] = Field(description="Relevant GitHub issues or PRs")
    synthesized_fix: str = Field(description="A synthesized strategy for fixing the error based on research")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")

class OpenAIAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-2024-04-09"):
        super().__init__(api_key, model)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
        # Define tools for OpenAI function calling
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_stack_overflow",
                    "description": "Search Stack Overflow for similar error messages and solutions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "error_query": {"type": "string", "description": "The error message or query"}
                        },
                        "required": ["error_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "General web search for documentation and articles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_similar_bugs",
                    "description": "Find similar bugs in GitHub repositories.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "error_message": {"type": "string", "description": "The error message"}
                        },
                        "required": ["error_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_page_content",
                    "description": "Read the content of a specific URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to read"}
                        },
                        "required": ["url"]
                    }
                }
            }
        ]

    def format_prompt(self, context: Dict[str, Any]) -> str:
        """Format the system prompt."""
        error_info = context.get("error_info", "No specific error provided.")
        code_context = context.get("code_context", "")
        
        prompt = f"""
        You are an expert Web Research Agent. Your goal is to find solutions for coding errors by searching the web.
        
        Error Information:
        {error_info}
        
        Code Context:
        {code_context}
        
        Task:
        1. Search Stack Overflow for the specific error message.
        2. Search for official documentation related to the failing library or function.
        3. Check for similar GitHub issues if applicable.
        4. Read the content of promising search results to understand the fix.
        5. Synthesize a solution strategy based on the best findings.
        
        Prioritize solutions that are:
        - Recent (last 2-3 years)
        - Highly upvoted or accepted
        - Directly relevant to the specific error and context
        """
        return prompt

    async def _execute_tool(self, tool_call: Any) -> Any:
        """Execute local MCP tools based on OpenAI tool call."""
        try:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {name} with args: {args}")
            
            if name == "search_stack_overflow":
                return search_stack_overflow(args["error_query"])
            elif name == "search_web":
                return search_web(args["query"])
            elif name == "find_similar_bugs":
                return find_similar_bugs(args["error_message"])
            elif name == "get_page_content":
                return get_page_content(args["url"])
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing {name}: {str(e)}"

    async def _call_provider(self, prompt: str) -> str:
        """
        Call OpenAI with tool use loop.
        """
        messages = [
            {"role": "system", "content": "You are a helpful research assistant."},
            {"role": "user", "content": prompt}
        ]
        
        max_turns = 5
        current_turn = 0
        
        while current_turn < max_turns:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                messages.append(message)
                
                for tool_call in message.tool_calls:
                    result = await self._execute_tool(tool_call)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                
                current_turn += 1
            else:
                return message.content

        return "Research incomplete: Max tool turns reached."

    async def _stream_provider(self, prompt: str) -> AsyncGenerator[str, None]:
        """Streaming implementation."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web research.
        """
        try:
            prompt = self.format_prompt(context)
            
            json_instruction = """
            
            Finally, output your research findings as a valid JSON object matching this structure:
            {
                "stack_overflow_solutions": [{"title": "str", "url": "str", "relevance": float}],
                "documentation_links": ["str"],
                "github_solutions": [{"title": "str", "url": "str"}],
                "synthesized_fix": "str",
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
            research = WebResearch(**data)
            
            return research.model_dump()
            
        except Exception as e:
            logger.error(f"OpenAI research failed: {e}")
            return {
                "stack_overflow_solutions": [],
                "documentation_links": [],
                "github_solutions": [],
                "synthesized_fix": f"Research failed: {str(e)}",
                "confidence_score": 0.0
            }
