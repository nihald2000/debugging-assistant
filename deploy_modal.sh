#!/bin/bash
# Deploy DebugGenie to Modal (Linux/Mac/WSL only)

echo "🚀 Deploying DebugGenie to Modal..."

# Check if Modal is configured
if ! modal config show > /dev/null 2>&1; then
    echo "❌ Modal not configured. Run: modal setup"
    exit 1
fi

# Create volume if needed
echo "📦 Creating volume..."
modal volume create debuggenie-data 2>/dev/null || echo "Volume already exists"

# Deploy MCP servers
echo "🔧 Deploying MCP servers..."
modal deploy modal_deploy_mcp.py

echo "✅ Deployment complete!"
echo "View at: https://modal.com/apps"
