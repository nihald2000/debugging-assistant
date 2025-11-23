# DebugGenie Deployment Guide

## Deployment Options

1. **Modal** - Serverless GPU/CPU functions
2. **HuggingFace Spaces** - Gradio app hosting
3. **Docker** - Self-hosted containers
4. **Local** - Development environment

---

## 1. Modal Deployment

### Prerequisites

```bash
# Install Modal
pip install modal

# Authenticate
modal setup
# Follow prompts to get token from https://modal.com
```

### Deploy MCP Servers

```bash
# Deploy all three MCP servers (filesystem, github, websearch)
modal deploy modal_deploy_mcp.py
```

Expected output:
```
✓ Created filesystem_mcp
✓ Created github_mcp  
✓ Created websearch_mcp
View at: https://modal.com/apps/debuggenie-mcp
```

### Configure Secrets

In Modal dashboard (https://modal.com/secrets):

1. Create secret: `debuggenie-secrets`
2. Add keys:
   - `GITHUB_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   - `GOOGLE_AI_API_KEY`
   - `ELEVENLABS_API_KEY`

### Create Persistent Volume

```bash
modal volume create debuggenie-data
```

Upload your codebase:
```bash
modal volume put debuggenie-data local_path/ /data/
```

### Deploy Main Application

Create `modal_app.py`:

```python
import modal
from config.settings import settings

app = modal.App("debuggenie-app")

image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("debuggenie-secrets")],
    gpu="T4",  # For Gemini/Claude heavy tasks
    timeout=600
)
@modal.web_endpoint(method="POST")
def analyze_error(error_info: dict):
    from core.orchestrator import DebugOrchestrator
    import asyncio
    
    orch = DebugOrchestrator(
        anthropic_key=settings.ANTHROPIC_API_KEY,
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GOOGLE_AI_API_KEY
    )
    
    result = asyncio.run(orch.orchestrate(error_info))
    return result
```

Deploy:
```bash
modal deploy modal_app.py
```

---

## 2. HuggingFace Spaces Deployment

### Prerequisites

1. Create account at https://huggingface.co
2. Create new Space: https://huggingface.co/new-space
   - Name: `debuggenie`
   - SDK: `Gradio`
   - Hardware: `CPU Basic` (free) or `T4 GPU` (paid)

### Prepare Repository

```bash
# Add HuggingFace as remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/debuggenie

# Create app.py as entry point (if not exists)
# HuggingFace looks for app.py with gradio.Interface
```

### Configure Secrets

In Space Settings → Repository secrets:

Add all keys from `.env.example`:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_AI_API_KEY`
- `GITHUB_TOKEN`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_AGENT_ID`

### Create requirements.txt (HF-specific)

HuggingFace Spaces may need pinned versions:

```txt
gradio==4.19.0
anthropic==0.40.0
google-generativeai==0.8.3
openai==1.54.0
elevenlabs==1.10.0
# ... rest of requirements
```

### Deploy

```bash
git push hf main
```

Monitor build at: `https://huggingface.co/spaces/YOUR_USERNAME/debuggenie`

### Enable Persistent Storage (Optional)

For caching/logs:

In Space Settings → Storage:
- Enable "Persistent Storage"
- Mount at `/data`

Update code to use `/data` for cache:
```python
CACHE_DIR = "/data/cache" if os.path.exists("/data") else "./cache"
```

---

## 3. Docker Deployment

### Build Images

```bash
docker-compose build
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with production keys
```

### Run Services

```bash
docker-compose up -d
```

Services:
- `filesystem` MCP on stdio
- `github` MCP on stdio
- `websearch` MCP on stdio

### Production Setup with Nginx

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  debuggenie:
    build: .
    ports:
      - "7860:7860"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_AI_API_KEY=${GOOGLE_AI_API_KEY}
    restart: always
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - debuggenie
```

Deploy:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 4. Claude Desktop Integration

### Install MCP Servers

```bash
# Build Docker images first
docker-compose build

# Copy config to Claude Desktop
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/
# (macOS path, adjust for Windows: %APPDATA%/Claude/)
```

### Configure Custom Project Path

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/project:/data",
        "mcp/filesystem"
      ]
    }
  }
}
```

### Verify Integration

1. Restart Claude Desktop
2. Open new conversation
3. Type: "List files in my project"
4. Claude should call the filesystem MCP tool

---

## Environment-Specific Configuration

### Development (.env.local)

```bash
DEBUG=True
LOG_LEVEL=DEBUG
ANTHROPIC_API_KEY=sk-ant-dev-key
```

### Staging (.env.staging)

```bash
DEBUG=False
LOG_LEVEL=INFO
ANTHROPIC_API_KEY=sk-ant-staging-key
```

### Production (.env.production)

```bash
DEBUG=False
LOG_LEVEL=WARNING
ANTHROPIC_API_KEY=sk-ant-prod-key
# Use production keys
```

Load specific environment:
```bash
export ENV=production
python -c "from config.settings import Settings; s = Settings(_env_file='.env.production'); print(s)"
```

---

## Monitoring & Logging

### Modal Logs

```bash
# View function logs
modal app logs debuggenie-app

# Stream logs in real-time
modal app logs debuggenie-app --follow
```

### HuggingFace Logs

Check Space logs at: `https://huggingface.co/spaces/YOUR_USERNAME/debuggenie/logs`

### Docker Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f debuggenie
```

### Application Logs

Logs stored in `debuggenie.log` (gitignored).

For production, configure loguru:

```python
from loguru import logger

logger.add(
    "/var/log/debuggenie.log",
    rotation="100 MB",
    retention="30 days",
    level="INFO"
)
```

---

## Performance Optimization

### Modal Optimization

```python
# Use GPU for heavy models
@app.function(gpu="A10G")

# Increase timeout for long tasks
@app.function(timeout=1800)  # 30 minutes

# Set concurrency limit
@app.function(concurrency_limit=10)
```

### HuggingFace Optimization

- Upgrade to GPU hardware for faster inference
- Enable "Always On" for zero cold starts
- Use caching for embeddings/vector stores

### Docker Optimization

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# Smaller final image
```

---

## Scaling

### Horizontal Scaling (Modal)

Modal auto-scales based on load. Configure limits:

```python
@app.function(
    concurrency_limit=100,  # Max concurrent executions
    container_idle_timeout=60  # Shutdown idle containers
)
```

### Load Balancing (Docker)

Use Docker Swarm or Kubernetes:

```bash
# Docker Swarm
docker swarm init
docker stack deploy -c docker-compose.yml debuggenie

# Scale service
docker service scale debuggenie_app=5
```

---

## Backup & Recovery

### Backup MCP Data (Modal)

```bash
# Download volume contents
modal volume get debuggenie-data /data/ ./backup/
```

### Backup Logs

```bash
# Archive logs
tar -czf logs-$(date +%Y%m%d).tar.gz debuggenie.log
```

### Disaster Recovery

1. Store `.env` in secure vault (1Password, AWS Secrets Manager)
2. Keep database backups (if using)
3. Version control all code
4. Document API keys rotation process

---

## Security Checklist

- [ ] All API keys in environment variables (not hardcoded)
- [ ] `.env` in `.gitignore`
- [ ] HTTPS enabled (production)
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] Secrets stored in Modal/HF Spaces secrets manager
- [ ] Regular dependency updates (`pip-audit`)
- [ ] Docker images scanned for vulnerabilities

---

## Rollback Procedure

### Modal

```bash
# List deployments
modal app list

# Rollback to previous version
modal deploy modal_app.py --tag v1.0.0
```

### HuggingFace

```bash
# Revert git commit
git revert HEAD
git push hf main
```

### Docker

```bash
# Use previous image tag
docker-compose pull debuggenie:v1.0.0
docker-compose up -d
```

---

## Post-Deployment Verification

### Health Check

Create `health_check.py`:

```python
import requests

def check_health():
    endpoints = [
        "https://your-modal-url.modal.run/health",
        "https://huggingface.co/spaces/YOUR_USERNAME/debuggenie"
    ]
    
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=10)
            print(f"✓ {url}: {resp.status_code}")
        except Exception as e:
            print(f"✗ {url}: {e}")

check_health()
```

### Smoke Tests

```bash
# Test analysis endpoint
curl -X POST https://your-app-url.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"error_info": "Test error"}'
```

---

## Support & Monitoring

### Set up Alerts

- Modal: Configure webhook alerts for function failures
- HuggingFace: Monitor Space status page
- Docker: Use Prometheus + Grafana

### Usage Analytics

Track:
- API call volume
- Average latency
- Error rates
- User feedback

---

## Cost Optimization

### Modal Pricing

- Billed per second of compute
- GPU more expensive than CPU
- Use `@app.function(cpu=0.25)` for lightweight tasks

### HuggingFace Pricing

- Free tier: CPU Basic
- Paid: T4 GPU ($0.60/hr), A10G ($3.15/hr)

### Tips

1. Cache LLM responses to reduce API calls
2. Use smaller models where possible
3. Implement request queuing to batch process
4. Set aggressive timeouts to prevent runaway costs
