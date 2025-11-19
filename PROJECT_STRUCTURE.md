# 🧞 DebugGenie - Project Structure

## Complete File Tree

```
debuggenie/
├── 📁 agents/                          # AI Agent Implementations
│   ├── __init__.py
│   ├── base_agent.py                   # Abstract base with retry, cache, metrics
│   ├── gemini_agent.py                 # Visual/screenshot analysis (Gemini 2.0)
│   ├── claude_agent.py                 # Codebase analysis (Claude Sonnet)
│   └── openai_agent.py                 # Web research (GPT-4)
│
├── 📁 config/                          # Configuration Management
│   ├── __init__.py
│   ├── api_keys.py                     # Pydantic API key validation
│   └── mcp_config.py                   # MCP server configuration
│
├── 📁 core/                            # Core Orchestration Logic
│   ├── __init__.py
│   ├── orchestrator.py                 # Multi-agent parallel execution
│   ├── solution_ranker.py              # Solution scoring & deduplication
│   └── error_parser.py                 # Error message parsing
│
├── 📁 mcp_servers/                     # Model Context Protocol Servers
│   ├── __init__.py
│   ├── filesystem_mcp.py               # File access, LlamaIndex search
│   ├── github_mcp.py                   # GitHub API integration
│   ├── web_search_mcp.py               # Stack Overflow, web search
│   ├── error_context_mcp.py            # Error context tools
│   └── log_parser_mcp.py               # Log parsing utilities
│
├── 📁 ui/                              # User Interface
│   ├── __init__.py
│   ├── gradio_interface.py             # Main Gradio UI
│   ├── chat_handler.py                 # Conversational chat management
│   └── components.py                   # Reusable UI components
│
├── 📁 visualization/                   # 3D Visualization
│   ├── __init__.py
│   ├── blaxel_generator.py             # 3D error flow (Plotly)
│   └── flow_analyzer.py                # AST-based flow analysis
│
├── 📁 voice/                           # Voice Explanations
│   ├── __init__.py
│   └── elevenlabs_tts.py               # ElevenLabs TTS integration
│
├── 📁 utils/                           # Utility Functions
│   ├── __init__.py
│   └── logger.py                       # Logging configuration
│
├── 📁 tests/                           # Test Suite
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_orchestrator.py
│   ├── test_mcp_servers.py
│   ├── test_visualization.py
│   └── test_integration.py
│
├── 📁 .cache/                          # Cache Directory
│   └── audio/                          # Cached voice files
│
├── 📄 app.py                           # 🚀 Main Application Entry Point
├── 📄 start.py                         # Quick-start launcher script
├── 📄 requirements.txt                 # Python dependencies
├── 📄 .env.example                     # Environment variable template
├── 📄 .gitignore                       # Git ignore rules
│
├── 📄 README.md                        # Project overview
├── 📄 SETUP.md                         # Detailed setup guide
├── 📄 IMPLEMENTATION_SUMMARY.md        # Complete implementation docs
│
├── 📄 modal_deploy.py                  # Modal Labs deployment
└── 📄 debuggenie.log                   # Application logs

```

## Component Responsibilities

### 🤖 Agents Layer
**Purpose:** Interface with AI models and execute specialized analysis

| Component | Model | Responsibility |
|-----------|-------|----------------|
| `GeminiAgent` | Gemini 2.0 Flash | Analyze screenshots, extract visual errors |
| `ClaudeAgent` | Claude 3.5 Sonnet | Deep codebase analysis, semantic search |
| `OpenAIAgent` | GPT-4 Turbo | Web research, Stack Overflow, GitHub |
| `BaseAgent` | - | Common functionality (retry, cache, metrics) |

### 🎯 Core Layer
**Purpose:** Orchestrate agents and synthesize results

| Component | Responsibility |
|-----------|----------------|
| `Orchestrator` | Parallel agent execution, result synthesis |
| `SolutionRanker` | Score, rank, and deduplicate solutions |
| `ErrorParser` | Parse and normalize error messages |

### 🔌 MCP Servers
**Purpose:** Provide tools for agents to access external resources

| Component | Provides |
|-----------|----------|
| `filesystem_mcp` | File reading, directory search, semantic search |
| `github_mcp` | Issue search, code search, PR data |
| `web_search_mcp` | Stack Overflow, DuckDuckGo, content extraction |

### 🎨 Visualization Layer
**Purpose:** Generate interactive visualizations

| Component | Output |
|-----------|--------|
| `blaxel_generator` | 3D error flow graphs (Plotly HTML) |
| `flow_analyzer` | Call graph analysis, recursion detection |

### 🔊 Voice Layer
**Purpose:** Generate audio explanations

| Component | Technology |
|-----------|------------|
| `elevenlabs_tts` | ElevenLabs API for natural TTS |

### 💬 UI Layer
**Purpose:** User interaction and display

| Component | Responsibility |
|-----------|----------------|
| `gradio_interface` | Main UI layout and event handling |
| `chat_handler` | Conversational AI, context management |
| `components` | Reusable UI widgets |

---

## Data Flow

```
User Input (Error + Screenshot)
         ↓
   Gradio Interface
         ↓
    Orchestrator
         ↓
    ┌────┴────┬─────────┐
    ↓         ↓         ↓
 Gemini    Claude    OpenAI
(Visual)  (Code)    (Web)
    ↓         ↓         ↓
    └────┬────┴─────────┘
         ↓
    Synthesizer (Claude)
         ↓
   Solution Ranker
         ↓
    ┌────┴────┬──────────┐
    ↓         ↓          ↓
  Chat    3D Viz     Voice
         ↓
   User sees results
```

---

## Configuration Files

### `.env` (Create from `.env.example`)
```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AI...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

### `requirements.txt`
- **UI:** gradio[mcp]
- **AI:** anthropic, google-generativeai, openai, elevenlabs
- **Search:** llama-index, duckduckgo-search
- **Viz:** plotly
- **Utils:** loguru, pydantic, tenacity, cachetools

---

## Entry Points

### Primary
```bash
python app.py              # Launch Gradio UI (port 7860)
```

### Alternative
```bash
python start.py            # Interactive launcher with checks
```

### Development
```bash
python -m pytest tests/    # Run test suite
```

---

## Key Files Reference

| File | Description | Lines |
|------|-------------|-------|
| `app.py` | Main entry point | ~25 |
| `core/orchestrator.py` | Multi-agent coordination | ~180 |
| `agents/base_agent.py` | Agent framework | ~150 |
| `agents/gemini_agent.py` | Visual analysis | ~180 |
| `agents/claude_agent.py` | Codebase analysis | ~220 |
| `agents/openai_agent.py` | Web research | ~200 |
| `ui/gradio_interface.py` | Main UI | ~340 |
| `ui/chat_handler.py` | Conversational AI | ~280 |
| `visualization/blaxel_generator.py` | 3D viz | ~120 |
| `voice/elevenlabs_tts.py` | Voice generation | ~200 |

**Total:** ~3,500+ lines of Python

---

## Dependencies Graph

```
app.py
  └─ ui/gradio_interface.py
      ├─ core/orchestrator.py
      │   ├─ agents/gemini_agent.py
      │   │   └─ agents/base_agent.py
      │   ├─ agents/claude_agent.py
      │   │   ├─ agents/base_agent.py
      │   │   └─ mcp_servers/filesystem_mcp.py
      │   └─ agents/openai_agent.py
      │       ├─ agents/base_agent.py
      │       ├─ mcp_servers/web_search_mcp.py
      │       └─ mcp_servers/github_mcp.py
      ├─ visualization/blaxel_generator.py
      ├─ visualization/flow_analyzer.py
      ├─ voice/elevenlabs_tts.py
      ├─ ui/chat_handler.py
      └─ config/api_keys.py
```

---

## External Integrations

| Service | Purpose | API Required |
|---------|---------|--------------|
| Anthropic | Claude for codebase analysis & synthesis | ✅ Yes |
| Google AI | Gemini for visual analysis | ✅ Yes |
| OpenAI | GPT-4 for web research | ✅ Yes |
| ElevenLabs | Voice generation | Optional |
| Stack Overflow | Error solutions | No (public API) |
| GitHub | Issue/code search | Optional (better with token) |
| DuckDuckGo | Web search | No (free) |

---

## Security & Best Practices

✅ **Implemented:**
- Path validation (filesystem MCP)
- API key validation (Pydantic)
- Rate limiting (all agents)
- Retry with exponential backoff
- Comprehensive error handling
- Input sanitization
- Logging (loguru)

⚠️ **Production Considerations:**
- Add user authentication
- Implement usage quotas
- Set up monitoring/alerting
- Add request rate limiting at app level
- Secure sensitive data in transit

---

## Performance Optimizations

- **Parallel Execution:** All agents run simultaneously (asyncio)
- **Caching:** API responses cached (1 hour TTL)
- **Streaming:** Long responses streamed to UI
- **Lazy Loading:** LlamaIndex built on-demand
- **Image Optimization:** Screenshots resized before analysis
- **Limited Results:** Max 50 nodes in visualizations

---

**📝 Last Updated:** Project completion
**🔢 Version:** 1.0.0
**👤 Built by:** Antigravity (Google DeepMind)
