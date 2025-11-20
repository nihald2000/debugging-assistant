import asyncio
from core.mcp_client import MCPClientManager
from loguru import logger

async def main():
    # Initialize Client Manager
    # This reads from claude_desktop_config.json
    manager = MCPClientManager()
    
    logger.info("Connecting to MCP servers...")
    await manager.connect_all()
    
    # List available tools from the 'modal' server
    logger.info("Discovering Modal tools...")
    modal_tools = [t for t in manager.tools if "modal" in t.get("name", "").lower() or "deploy" in t.get("name", "").lower()]
    
    for tool in modal_tools:
        logger.info(f"Found Tool: {tool['name']} - {tool['description']}")
        
    # Example: Deploy a script (Simulated call)
    # Assuming a tool named 'modal_deploy_script' or similar exists
    script_content = """
import modal
app = modal.App("hello-world")
@app.function()
def f():
    print("Hello from Modal!")
"""
    
    # In a real scenario, the agent would call this tool
    # await manager.execute_tool("modal_deploy", {"name": "hello-world", "script": script_content})
    
    logger.info("Usage example complete. Agents can now use these tools to deploy to Modal.")

if __name__ == "__main__":
    asyncio.run(main())
