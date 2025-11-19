# 🤗 HuggingFace Spaces Deployment Guide

## Quick Start

### 1. Create a New Space

1. Go to https://huggingface.co/new-space
2. Fill in details:
   - **Space name**: `debuggenie`
   - **SDK**: Gradio
   - **License**: MIT
   - **Visibility**: Public (or Private)
3. Click "Create Space"

### 2. Upload Files

Upload these files to your Space:

**Required:**
- `app.py`
- `requirements.txt`
- `README.md`
- All directories: `agents/`, `config/`, `core/`, `mcp_servers/`, `ui/`, `visualization/`, `voice/`, `utils/`

**Optional:**
- `.gitignore`
- `SETUP.md`
- `ARCHITECTURE.md`

### 3. Configure Secrets

In your Space settings (⚙️ Settings → Repository secrets):

Add the following secrets:

```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AI...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...  (optional)
```

### 4. Wait for Build

The Space will automatically:
1. Install dependencies from `requirements.txt`
2. Load your API keys from secrets
3. Start the Gradio server
4. Become available at: `https://huggingface.co/spaces/YOUR_USERNAME/debuggenie`

---

## Using Git (Alternative)

### Clone and Push

```bash
# Clone your Space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/debuggenie
cd debuggenie

# Copy DebugGenie files
cp -r /path/to/debuggenie/* .

# Commit and push
git add .
git commit -m "Initial DebugGenie deployment"
git push
```

---

## Configuration

### App Detection

The `app.py` automatically detects HuggingFace Spaces:

```python
IS_SPACES = os.getenv("SPACE_ID") is not None

if IS_SPACES:
    # Load secrets from environment
    os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
    # ...
```

### Queue Configuration

For Spaces, the queue is auto-configured:

```python
demo.queue(
    max_size=10,
    default_concurrency_limit=5
)
```

---

## Testing Deployment

### 1. Manual Test

Visit your Space URL and test with a sample error:

```
https://huggingface.co/spaces/YOUR_USERNAME/debuggenie
```

### 2. Automated Test

```bash
# Install test dependencies
pip install gradio-client requests

# Run test script
python test_hf_deployment.py https://huggingface.co/spaces/YOUR_USERNAME/debuggenie
```

### 3. Check Logs

In Space settings → Logs, verify:
- ✅ All dependencies installed
- ✅ API keys loaded
- ✅ Gradio server started
- ✅ No import errors

---

## Troubleshooting

### Build Fails

**Issue**: Dependencies not installing

**Solution**:
1. Check `requirements.txt` for compatibility
2. Pin exact versions
3. Remove any platform-specific deps

### API Keys Not Loading

**Issue**: Agents fail to initialize

**Solution**:
1. Verify secrets are set in Space settings
2. Check secret names match exactly
3. Restart Space after adding secrets

### Import Errors

**Issue**: Module not found

**Solution**:
1. Ensure all directories are uploaded
2. Check `__init__.py` files exist
3. Verify directory structure

### Memory Issues

**Issue**: Space runs out of memory

**Solution**:
1. Reduce queue size in `app.py`
2. Disable LlamaIndex caching
3. Request hardware upgrade (Settings → Hardware)

---

## Performance Optimization

### 1. Hardware Upgrade

Free tier: CPU Basic (2 vCPU, 16GB RAM)

For better performance:
- Settings → Hardware → Upgrade
- Recommended: CPU Upgrade (4 vCPU, 32GB RAM)

### 2. Queue Management

Adjust in `app.py`:

```python
demo.queue(
    max_size=5,  # Lower for free tier
    default_concurrency_limit=2
)
```

### 3. Cache Volume

Enable persistent storage:

Settings → Storage → Enable

This caches:
- Voice files
- LlamaIndex embeddings

---

## Security

### Secrets Management

✅ **DO:**
- Add all API keys as Space secrets
- Use environment variables only
- Never commit keys to git

❌ **DON'T:**
- Hardcode API keys
- Put keys in `.env` files in repo
- Share secrets in README

### Access Control

For private use:
- Settings → Visibility → Private
- Add collaborators if needed

---

## Monitoring

### Built-in Analytics

HuggingFace provides:
- User count
- Request volume
- Error rates

Access: Space page → Analytics tab

### Custom Metrics

Add to `app.py`:

```python
from loguru import logger

@demo.load
def on_load():
    logger.info("Space loaded")

# Track in Gradio events
def analyze_with_logging(*args):
    logger.info("Analysis started")
    result = handle_analyze(*args)
    logger.info("Analysis completed")
    return result
```

---

## Updating Deployment

### Via Web UI

1. Go to Files and versions
2. Edit files directly
3. Commit changes
4. Auto-rebuilds

### Via Git

```bash
# Make changes
git add .
git commit -m "Update: <description>"
git push

# Space auto-rebuilds
```

---

## Cost Optimization

### Free Tier

- ✅ Included: CPU Basic
- ⚠️ Limitations: 
  - Slower performance
  - No persistent storage
  - Sleep after inactivity

### Paid Tier

Upgrade for:
- Better performance
- Persistent storage
- No sleep timeout
- Priority support

---

## Community Features

### Add to Community

1. Make Space public
2. Add good README with examples
3. Add tags for discoverability
4. Share on HF community forums

### Enable Discussions

Settings → Discussions → Enable

Users can:
- Report bugs
- Request features
- Share use cases

---

## Quick Reference

| Action | Command/Link |
|--------|-------------|
| Create Space | https://huggingface.co/new-space |
| View logs | Space → Settings → Logs |
| Add secrets | Space → Settings → Repository secrets |
| Upgrade hardware | Space → Settings → Hardware |
| Test deployment | `python test_hf_deployment.py <URL>` |

---

**🎉 Your DebugGenie Space is now live!**
