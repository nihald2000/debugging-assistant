import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config.mcp_config import mcp_config
    print("[OK] MCP Config loaded successfully")
    print(f"   - Servers: {list(mcp_config.servers.keys())}")
except Exception as e:
    print(f"[FAIL] MCP Config failed: {e}")

try:
    from utils.logger import log
    log.info("[OK] Logger test message")
    print("[OK] Logger loaded successfully")
except Exception as e:
    print(f"[FAIL] Logger failed: {e}")

# Note: We skip api_keys verification here because it requires actual env vars which might not be set yet.
print("[WARN] Skipping API Key verification (requires .env)")
