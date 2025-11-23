# DebugGenie Testing Guide

## Prerequisites

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required API keys:
- `ANTHROPIC_API_KEY` - For Claude agent
- `OPENAI_API_KEY` - For OpenAI Swarm agents
- `GOOGLE_AI_API_KEY` - For Gemini agent
- `GITHUB_TOKEN` - For GitHub MCP server
- `ELEVENLABS_API_KEY` - For voice features
- `ELEVENLABS_AGENT_ID` - Your ElevenLabs agent ID

---

## Unit Testing

### Test Individual Agents

#### 1. Test Claude Agent (smolagents)
```bash
python -c "
from agents.claude_agent import ClaudeAgent
from config.settings import settings
import asyncio

async def test():
    agent = ClaudeAgent(api_key=settings.ANTHROPIC_API_KEY)
    context = {
        'error_info': 'TypeError: unsupported operand type(s) for +: int and str',
        'visual_analysis': {}
    }
    result = await agent.analyze(context)
    print(result)

asyncio.run(test())
"
```

#### 2. Test Gemini Agent
```bash
python -c "
from agents.gemini_agent import GeminiAgent
from config.settings import settings
import asyncio

async def test():
    agent = GeminiAgent(api_key=settings.GOOGLE_AI_API_KEY)
    context = {
        'error_screenshot': 'path/to/screenshot.png',
        'error_info': 'React useEffect infinite loop'
    }
    result = await agent.analyze(context)
    print(result)

asyncio.run(test())
"
```

#### 3. Test OpenAI Swarm
```bash
python -c "
from agents.openai_agent import OpenAIAgent
from config.settings import settings
import asyncio

async def test():
    agent = OpenAIAgent(api_key=settings.OPENAI_API_KEY)
    context = {'error_info': 'AttributeError: module object has no attribute'}
    result = await agent.analyze(context)
    print(result)

asyncio.run(test())
"
```

---

## Integration Testing

### Test MCP Servers (Dockerized)

#### 1. Build Docker Images
```bash
docker-compose build
```

#### 2. Test Filesystem MCP
```bash
docker run -i --rm -v ./:/data mcp/filesystem
# In another terminal, send test JSON-RPC request
```

#### 3. Test GitHub MCP
```bash
export GITHUB_TOKEN=your_token
docker run -i --rm -e GITHUB_TOKEN mcp/github
```

#### 4. Test WebSearch MCP
```bash
docker run -i --rm mcp/websearch
```

### Test MCP Client Integration

```bash
python -c "
from core.mcp_client import MCPClientManager
import asyncio

async def test():
    manager = MCPClientManager()
    await manager.connect_all()
    print(f'Connected to {len(manager.servers)} servers')
    print(f'Available tools: {len(manager.tools)}')

asyncio.run(test())
"
```

---

## Modal Testing

### Test Modal Sandboxes

```bash
# Ensure Modal is configured
modal setup

# Test sandbox execution
python -c "
from core.modal_sandbox import SafeCodeExecutor
import asyncio

async def test():
    executor = SafeCodeExecutor(timeout=30)
    code = 'print(\"Hello from Modal Sandbox\")'
    
    from modal import App
    app = App('test')
    with app.run():
        stdout, stderr, rc = executor.execute(code)
        print(f'Return Code: {rc}')
        print(f'Output: {stdout}')

asyncio.run(test())
"
```

### Test Modal MCP Deployment

```bash
# Deploy MCP servers to Modal
modal deploy modal_deploy_mcp.py

# Test deployed endpoints
python modal_mcp_usage.py
```

---

## Voice Testing

### Test ElevenLabs Conversational AI

```bash
# Ensure ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID are set
python voice/conversational_agent.py

# Expected:
# - Microphone input active
# - Agent responds with voice
# - Interruptions handled
# - Multi-language support working
```

### Test Gemini Multimodal Live

```bash
python agents/gemini_live.py

# Expected:
# - Webcam feed captured
# - Audio input/output working
# - Real-time suggestions provided
```

---

## End-to-End Testing

### Test Full Orchestrator Flow

```bash
python start.py
```

Then in UI:
1. Upload error screenshot
2. Provide error description
3. Click "Analyze Error"
4. Verify all agents run in parallel
5. Check synthesis report quality

### Test Voice Interface

```bash
python app.py
```

In Gradio UI:
1. Click "🎤 Talk to DebugGenie"
2. Describe error verbally
3. Verify agent asks clarifying questions
4. Check interruption handling
5. Test multi-language (switch languages mid-conversation)

---

## Performance Testing

### Latency Benchmarks

```bash
python -c "
import time
import asyncio
from core.orchestrator import DebugOrchestrator
from config.settings import settings

async def benchmark():
    orch = DebugOrchestrator(
        anthropic_key=settings.ANTHROPIC_API_KEY,
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GOOGLE_AI_API_KEY
    )
    
    context = {'error_info': 'IndexError: list index out of range'}
    
    start = time.time()
    result = await orch.orchestrate(context)
    end = time.time()
    
    print(f'Total time: {end - start:.2f}s')
    print(f'Result: {result}')

asyncio.run(benchmark())
"
```

Expected latency:
- Claude agent: < 5s
- Gemini agent: < 3s
- OpenAI Swarm: < 8s
- Total orchestration: < 10s (parallel execution)

---

## Automated Testing (CI/CD)

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Test DebugGenie

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run unit tests
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        GOOGLE_AI_API_KEY: ${{ secrets.GOOGLE_AI_API_KEY }}
      run: python -m pytest tests/
```

---

## Troubleshooting

### Common Issues

**Docker MCP not connecting:**
```bash
# Check Docker daemon
docker info

# Check container logs
docker logs <container_id>
```

**Modal authentication fails:**
```bash
modal token set --token-id <id> --token-secret <secret>
```

**ElevenLabs WebSocket disconnects:**
- Check API key validity
- Verify agent ID is correct
- Ensure stable internet connection

**Gemini Live API fails:**
- Check GOOGLE_API_KEY is set
- Verify webcam/mic permissions
- Test with `ls /dev/video*` (Linux) or check Privacy settings (macOS/Windows)

---

## Test Coverage Goals

- Unit tests: > 80%
- Integration tests: All MCP servers
- End-to-end: Full orchestrator flow
- Performance: < 10s total latency
- Voice: Interruption and multi-language support
