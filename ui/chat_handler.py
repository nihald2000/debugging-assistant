import re
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import anthropic
from config.api_keys import api_config

class ChatHandler:
    def __init__(self):
        self.conversation_history = []
        self.current_error = None
        self.current_solutions = []
        self.current_analysis = None
        self.codebase_context = {}
        
        # Initialize Claude for conversational responses
        self.claude_client = anthropic.AsyncAnthropic(api_key=api_config.anthropic_api_key)
        
    def is_error_message(self, message: str) -> bool:
        """Detect if message contains an error."""
        error_patterns = [
            r'Traceback \(most recent call last\)',
            r'Error:',
            r'Exception:',
            r'at line \d+',
            r'File ".*", line \d+',
            r'\w+Error:',
            r'\w+Exception:',
            r'failed with exit code',
            r'SyntaxError',
            r'TypeError',
            r'ValueError',
            r'AttributeError',
            r'ImportError',
            r'KeyError',
            r'IndexError',
        ]
        
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in error_patterns)
    
    def is_code_snippet(self, message: str) -> bool:
        """Detect if message is primarily code."""
        # Check for code indicators
        code_indicators = [
            message.count('\n') > 3,  # Multi-line
            re.search(r'def \w+\(', message),  # Function definition
            re.search(r'class \w+:', message),  # Class definition
            re.search(r'import \w+', message),  # Imports
            re.search(r'from \w+ import', message),
            message.count('(') > 2 and message.count(')') > 2,  # Function calls
        ]
        
        return sum(code_indicators) >= 2
    
    async def process_message(self, message: str, history: List[List[str]]) -> Tuple[List[List[str]], str]:
        """
        Process user message and generate response.
        
        Returns:
            Tuple of (updated_history, status_message)
        """
        try:
            # Add user message to history
            new_history = history + [[message, None]]
            
            # Determine intent and route
            if self.is_error_message(message):
                response = await self.handle_new_error(message)
                status = "🔍 New error detected - starting analysis..."
            elif self.current_error and self._is_followup_question(message):
                response = await self.handle_followup(message)
                status = "💬 Answering follow-up question..."
            elif self.is_code_snippet(message):
                response = await self.handle_code_snippet(message)
                status = "📝 Analyzing code snippet..."
            else:
                response = await self.handle_general_chat(message)
                status = "💭 Processing..."
            
            # Update history with response
            new_history[-1][1] = response
            
            return new_history, status
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            error_history = history + [[message, f"❌ Error: {str(e)}"]]
            return error_history, f"Status: ❌ Error - {str(e)}"
    
    def _is_followup_question(self, message: str) -> bool:
        """Detect if this is a follow-up question about current error."""
        followup_indicators = [
            r'\bwhy\b',
            r'\bhow\b',
            r'\bwhat if\b',
            r'\bcan (?:i|you)\b',
            r'\bshould i\b',
            r'\bmore details?\b',
            r'\bexplain\b',
            r'\bclarify\b',
            r'\bin step \d+\b',
        ]
        
        return any(re.search(pattern, message.lower()) for pattern in followup_indicators)
    
    async def handle_new_error(self, error_text: str) -> str:
        """Handle a newly pasted error message."""
        self.current_error = error_text
        
        response = f"""
I've detected an error in your message! Let me analyze it.

**Error Preview:**
```
{error_text[:300]}...
```

Would you like me to:
1. 🔍 Run a full multi-agent analysis
2. 🎯 Quick diagnosis only
3. 🌐 Search for similar errors online

You can also upload a screenshot or paste additional code context for better results.
        """
        
        return response.strip()
    
    async def handle_followup(self, question: str) -> str:
        """Answer follow-up questions about the current error/solution."""
        if not self.current_error and not self.current_solutions:
            return "I don't have any active error analysis. Please paste an error message first."
        
        # Build context for Claude
        context_prompt = f"""
You are DebugGenie, an AI debugging assistant. Answer the user's follow-up question about their error.

Current Error:
{self.current_error[:500] if self.current_error else 'None'}

Current Solutions:
{self.current_solutions[:3] if self.current_solutions else 'None yet'}

User Question:
{question}

Provide a helpful, concise answer. Use markdown formatting. If you don't have enough context, ask for clarification.
        """
        
        try:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[{"role": "user", "content": context_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API failed: {e}")
            return f"I'm having trouble processing that question. Error: {str(e)}"
    
    async def handle_code_snippet(self, code: str) -> str:
        """Analyze a code snippet."""
        prompt = f"""
You are a code review expert. Analyze this code snippet and identify potential issues:

```
{code}
```

Provide:
1. Quick assessment (working/has issues)
2. Potential bugs or anti-patterns
3. Suggestions for improvement

Be concise and use markdown.
        """
        
        try:
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return "I can see you've shared code, but I'm having trouble analyzing it right now."
    
    async def handle_general_chat(self, message: str) -> str:
        """Handle general conversation."""
        
        # Check for common questions
        lower_msg = message.lower()
        
        if any(word in lower_msg for word in ['hello', 'hi', 'hey']):
            return """
👋 Hello! I'm DebugGenie, your AI debugging assistant.

I can help you:
- 🐛 Debug errors and exceptions
- 🔍 Analyze error screenshots
- 💡 Find solutions from Stack Overflow and GitHub
- 🎨 Visualize error flow in 3D
- 🔊 Explain fixes with voice guidance

Just paste your error message or upload a screenshot to get started!
            """.strip()
        
        elif 'help' in lower_msg:
            return """
**How to use DebugGenie:**

1. **Paste Error**: Copy your error message or stack trace
2. **Upload Screenshot** (optional): Add IDE/browser screenshots
3. **Click Analyze**: Multi-agent AI will investigate
4. **Review Solutions**: Get ranked fixes with confidence scores
5. **Ask Questions**: I can clarify any solution

**Example:**
```
Paste: "TypeError: 'NoneType' object is not subscriptable"
→ I'll analyze and suggest fixes
```

What error are you facing?
            """.strip()
        
        elif 'features' in lower_msg or 'capabilities' in lower_msg:
            return """
**DebugGenie Features:**

🤖 **Multi-Agent Analysis**
- Gemini 2.0: Visual/screenshot analysis
- Claude Sonnet: Deep codebase search
- GPT-4: Web research & documentation

🎨 **Visualizations**
- 3D error flow graphs
- Interactive call stacks
- Code dependency traces

🔊 **Voice Explanations**
- Audio walkthroughs via ElevenLabs
- Step-by-step voice guides

💬 **Smart Chat**
- Context-aware conversations
- Follow-up question support
- Solution clarification

Try it now by pasting an error!
            """.strip()
        
        else:
            # Use Claude for general questions
            try:
                response = await self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=512,
                    messages=[{
                        "role": "user", 
                        "content": f"As DebugGenie, a debugging assistant, respond to: {message}"
                    }]
                )
                return response.content[0].text
            except Exception as e:
                return "I'm here to help debug errors! Paste an error message to get started."
    
    def update_context(self, error: Optional[str] = None, solutions: Optional[List] = None, 
                      analysis: Optional[Dict] = None):
        """Update the conversation context."""
        if error:
            self.current_error = error
        if solutions:
            self.current_solutions = solutions
        if analysis:
            self.current_analysis = analysis
    
    def reset_context(self):
        """Clear current debugging context."""
        self.current_error = None
        self.current_solutions = []
        self.current_analysis = None
        logger.info("Chat context reset")
    
    def get_context_summary(self) -> str:
        """Get a summary of current context."""
        summary = "**Current Context:**\n\n"
        
        if self.current_error:
            summary += f"- 🐛 Active Error: {self.current_error[:50]}...\n"
        else:
            summary += "- No active error\n"
        
        if self.current_solutions:
            summary += f"- ✅ {len(self.current_solutions)} solutions found\n"
        else:
            summary += "- No solutions yet\n"
        
        return summary
