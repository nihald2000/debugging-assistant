# 🧞 DebugGenie - Complete Setup Guide

## Overview
DebugGenie is a multi-agent AI debugging assistant that uses Claude, Gemini, and GPT-4 to analyze and solve coding errors. It features visual analysis, codebase exploration, web research, 3D visualization, and voice explanations.

## Features
- **🎯 Multi-Agent Analysis**: Three specialized AI agents work in parallel
  - Gemini 2.0 Flash: Visual/screenshot analysis
  - Claude Sonnet 4: Codebase deep-dive with semantic search
  - GPT-4: Web research and documentation lookup
  
- **🎨 3D Error Visualization**: Interactive call flow graphs using Plotly
- **🔊 Voice Explanations**: AI-generated audio walkthroughs via ElevenLabs
- **💬 Interactive Chat**: Gradio-based conversational UI
- **📊 Detailed Analysis**: Metrics, confidence scores, and execution flow

## Prerequisites
- Python 3.9+
- API Keys for:
  - Anthropic (Claude)
  - Google AI Studio (Gemini)
  - OpenAI (GPT-4)
  - ElevenLabs (optional, for voice)

## Installation

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd debuggenie
python -m venv venv
```

### 2. Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```

**Unix/MacOS:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_AI_API_KEY=your_google_ai_key_here
OPENAI_API_KEY=your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here  # Optional
```

## Usage

### Start the Application
```bash
python app.py
```

The interface will launch at `http://localhost:7860`

### Example Workflow
1. **Paste Error**: Copy your error message/stack trace into the code editor
2. **Upload Screenshot** (optional): Take a screenshot of your IDE/browser error
3. **Click Analyze**: The multi-agent system will analyze in parallel
4. **Review Results**:
   - Chat: Natural language explanation
   - Solutions: Ranked fixes with confidence scores
   - 3D Visualization: Interactive error flow
   - Voice: Audio walkthrough (if ElevenLabs configured)

## Architecture

```
├── agents/              # AI agents
│   ├── base_agent.py   # Abstract base with retry, caching, metrics
│   ├── gemini_agent.py # Visual analysis
│   ├── claude_agent.py # Codebase analysis with tool calling
│   └── openai_agent.py # Web research
├── core/               # Core logic
│   ├── orchestrator.py # Parallel execution and synthesis
│   └── solution_ranker.py # Scoring and deduplication
├── visualization/      # 3D rendering
│   ├── blaxel_generator.py # Plotly 3D graphs
│   └── flow_analyzer.py    # AST-based flow analysis
├── voice/              # Audio generation
│   └── elevenlabs_tts.py
├── mcp_servers/        # MCP tools
│   ├── filesystem_mcp.py
│   ├── github_mcp.py
│   └── web_search_mcp.py
└── ui/                 # Gradio interface
    └── gradio_interface.py
```

## API Key Setup

### Anthropic (Claude)
1. Visit https://console.anthropic.com/
2. Create an account and get API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### Google AI (Gemini)
1. Visit https://makersuite.google.com/app/apikey
2. Create API key
3. Add to `.env`: `GOOGLE_AI_API_KEY=AI...`

### OpenAI (GPT-4)
1. Visit https://platform.openai.com/api-keys
2. Create API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`

### ElevenLabs (Voice - Optional)
1. Visit https://elevenlabs.io/
2. Get API key from profile
3. Add to `.env`: `ELEVENLABS_API_KEY=...`

## Troubleshooting

### Import Errors
```bash
pip install -r requirements.txt --upgrade
```

### Missing API Keys
- The system will work in degraded mode without ElevenLabs
- Core agents (Claude, Gemini, OpenAI) are required

### Visualization Not Loading
- Check browser console for errors
- Ensure Plotly is installed: `pip install plotly`

### Async Errors
- Make sure you're using Python 3.9+
- Install asyncio: `pip install asyncio`

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Linting
```bash
pip install black
black .
```

## Deployment

### Modal Labs
```bash
modal deploy modal_deploy.py
```

### HuggingFace Spaces
1. Create new Space on HuggingFace
2. Upload files
3. Add Secrets (API keys) in Settings

## Contributing
1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License
MIT License

## Support
For issues and questions:
- GitHub Issues: [your-repo]/issues
- Documentation: See `/docs` folder

## Acknowledgments
- Built with Gradio, LlamaIndex, and Plotly
- Powered by Claude, Gemini, and GPT-4
- Voice by ElevenLabs
