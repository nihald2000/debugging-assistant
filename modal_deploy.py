import modal
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Environment configuration
ENV = os.getenv("DEPLOY_ENV", "production")
IS_PROD = ENV == "production"

# Modal image configuration
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "gradio==4.44.0",
        "anthropic==0.40.0",
        "google-generativeai==0.8.3",
        "openai==1.54.0",
        "elevenlabs==1.10.0",
        "llama-index==0.11.0",
        "llama-index-vector-stores-chroma==0.2.0",
        "plotly==5.24.0",
        "loguru==0.7.2",
        "pydantic==2.9.0",
        "pydantic-settings==2.5.0",
        "python-dotenv==1.0.0",
        "requests==2.32.0",
        "beautifulsoup4==4.12.0",
        "pygments==2.18.0",
        "cachetools",
        "tenacity",
        "Pillow==10.4.0",
        "duckduckgo-search==6.3.5",
    )
    .copy_local_dir("agents", "/root/debuggenie/agents")
    .copy_local_dir("config", "/root/debuggenie/config")
    .copy_local_dir("core", "/root/debuggenie/core")
    .copy_local_dir("mcp_servers", "/root/debuggenie/mcp_servers")
    .copy_local_dir("ui", "/root/debuggenie/ui")
    .copy_local_dir("visualization", "/root/debuggenie/visualization")
    .copy_local_dir("voice", "/root/debuggenie/voice")
    .copy_local_dir("utils", "/root/debuggenie/utils")
    .run_commands("mkdir -p /root/.cache/audio")
)

app = modal.App("debuggenie" if IS_PROD else "debuggenie-dev")

# Shared volume for caching
cache_volume = modal.Volume.from_name(
    "debuggenie-cache" if IS_PROD else "debuggenie-cache-dev",
    create_if_missing=True
)

# Monitoring setup
class Monitor:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.api_usage = {
            "anthropic": 0,
            "google": 0,
            "openai": 0,
            "elevenlabs": 0
        }
    
    def log_request(self):
        self.request_count += 1
        print(f"📊 Total requests: {self.request_count}")
    
    def log_error(self, error: str):
        self.error_count += 1
        print(f"❌ Error #{self.error_count}: {error}")
    
    def log_api_call(self, provider: str):
        if provider in self.api_usage:
            self.api_usage[provider] += 1
            print(f"🔑 API call to {provider}: {self.api_usage[provider]} total")

monitor = Monitor()

# MCP Server configuration
@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("debuggenie-secrets"),
    ],
    volumes={"/root/.cache": cache_volume},
    cpu=2.0,
    memory=4096,
    timeout=600,
    container_idle_timeout=300,
    allow_concurrent_inputs=10,
    keep_warm=1 if IS_PROD else 0,
)
@modal.web_server(8000, startup_timeout=60)
def serve():
    import sys
    sys.path.insert(0, "/root/debuggenie")
    
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import gradio as gr
    from ui.gradio_interface import create_interface
    from loguru import logger
    import time
    
    # Configure logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    fastapi_app = FastAPI(title="DebugGenie API")
    
    # CORS configuration
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not IS_PROD else [
            "https://debuggenie.app",
            "https://*.modal.run"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    @fastapi_app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        monitor.log_request()
        
        logger.info(f"Request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"Completed in {process_time:.2f}s - Status: {response.status_code}")
            return response
        except Exception as e:
            monitor.log_error(str(e))
            logger.error(f"Request failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    # Health check endpoint
    @fastapi_app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": ENV,
            "requests": monitor.request_count,
            "errors": monitor.error_count,
            "api_usage": monitor.api_usage
        }
    
    # Metrics endpoint
    @fastapi_app.get("/metrics")
    async def metrics():
        return {
            "total_requests": monitor.request_count,
            "error_rate": monitor.error_count / max(monitor.request_count, 1),
            "api_usage": monitor.api_usage,
            "cache_status": "active"
        }
    
    # Create Gradio interface
    demo = create_interface()
    demo.queue(
        max_size=20 if IS_PROD else 5,
        default_concurrency_limit=10 if IS_PROD else 3
    )
    
    # Mount Gradio app
    app = gr.mount_gradio_app(fastapi_app, demo, path="/")
    
    logger.info(f"🚀 DebugGenie started in {ENV} mode")
    
    return app

# CLI deployment helper
@app.local_entrypoint()
def main(env: str = "production"):
    global ENV, IS_PROD
    ENV = env
    IS_PROD = env == "production"
    print(f"🚀 Deploying DebugGenie to Modal ({ENV} environment)")
    print(f"📦 Image: {image}")
    print(f"🔑 Secrets: debuggenie-secrets")
    print(f"💾 Cache volume: debuggenie-cache{'-dev' if not IS_PROD else ''}")
    print("\n✅ Deployment configuration validated")

# Dev server for local testing
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("debuggenie-secrets")],
)
def test_agents():
    import sys
    sys.path.insert(0, "/root/debuggenie")
    
    from core.orchestrator import DebugOrchestrator
    
    print("🧪 Testing agent initialization...")
    orchestrator = DebugOrchestrator()
    print("✅ Orchestrator initialized")
    print(f"✅ Agents loaded: Gemini, Claude, OpenAI")
    return True

# Scheduled cache cleanup
@app.function(
    image=image,
    schedule=modal.Cron("0 2 * * *"),  # 2 AM daily
    volumes={"/root/.cache": cache_volume},
)
def cleanup_cache():
    import shutil
    from pathlib import Path
    
    cache_dir = Path("/root/.cache/audio")
    
    if cache_dir.exists():
        total_size = sum(f.stat().st_size for f in cache_dir.glob("*.mp3"))
        file_count = len(list(cache_dir.glob("*.mp3")))
        
        print(f"🧹 Cache cleanup: {file_count} files, {total_size / 1024 / 1024:.2f} MB")
        
        # Remove files older than 7 days
        import time
        week_ago = time.time() - (7 * 24 * 60 * 60)
        
        removed = 0
        for file in cache_dir.glob("*.mp3"):
            if file.stat().st_mtime < week_ago:
                file.unlink()
                removed += 1
        
        print(f"✅ Removed {removed} old cache files")
        cache_volume.commit()

# Batch error analysis (for high-volume usage)
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("debuggenie-secrets")],
    volumes={"/root/.cache": cache_volume},
    cpu=4.0,
    memory=8192,
    timeout=1800,
)
async def batch_analyze(error_list: list[Dict[str, Any]]):
    import sys
    sys.path.insert(0, "/root/debuggenie")
    
    from core.orchestrator import DebugOrchestrator
    import asyncio
    
    orchestrator = DebugOrchestrator()
    
    print(f"🔄 Processing batch of {len(error_list)} errors")
    
    results = []
    for idx, error_context in enumerate(error_list):
        print(f"Analyzing error {idx + 1}/{len(error_list)}")
        result = await orchestrator.orchestrate_debug(error_context)
        results.append(result.model_dump())
    
    print(f"✅ Batch analysis complete")
    return results
