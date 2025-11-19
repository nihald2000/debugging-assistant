"""
HuggingFace Spaces MCP Connection Test
Tests MCP server connectivity after deployment
"""

from gradio_client import Client
import os
import sys

def test_mcp_connection(space_url: str):
    """Test connection to deployed HuggingFace Space"""
    
    print(f"🧪 Testing MCP connection to: {space_url}")
    print("=" * 60)
    
    try:
        # Connect to the Space
        client = Client(space_url)
        print("✅ Connected to HuggingFace Space")
        
        # Test basic prediction
        print("\n📤 Sending test error...")
        test_error = """
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    result = process_data(None)
  File "test.py", line 2, in process_data
    return data['key']
TypeError: 'NoneType' object is not subscriptable
        """
        
        result = client.predict(
            error_text=test_error,
            screenshot=None,
            codebase_files=None,
            api_name="/analyze"
        )
        
        print("✅ Received response from Space")
        print(f"\n📊 Response preview:")
        print(f"  - Chat messages: {len(result[0]) if result[0] else 0}")
        print(f"  - Solutions HTML: {len(result[1]) if result[1] else 0} chars")
        print(f"  - Status: {result[5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_health_endpoint(space_url: str):
    """Test health endpoint"""
    import requests
    
    # Convert Space URL to API endpoint
    if "huggingface.co" in space_url:
        api_url = space_url.replace("huggingface.co/spaces/", "")
        api_url = f"https://{api_url.replace('/', '-')}.hf.space/health"
    else:
        api_url = f"{space_url}/health"
    
    print(f"\n🏥 Testing health endpoint: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"⚠️  Health check returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Health endpoint not available: {e}")
        return False

def main():
    """Run all tests"""
    
    # Get Space URL from command line or use default
    if len(sys.argv) > 1:
        space_url = sys.argv[1]
    else:
        print("Usage: python test_hf_deployment.py <SPACE_URL>")
        print("\nExample:")
        print("  python test_hf_deployment.py https://huggingface.co/spaces/USERNAME/debuggenie")
        sys.exit(1)
    
    print("\n🧞 DebugGenie HuggingFace Spaces Test")
    print("=" * 60)
    
    # Run tests
    mcp_ok = test_mcp_connection(space_url)
    health_ok = test_health_endpoint(space_url)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"  MCP Connection: {'✅ PASS' if mcp_ok else '❌ FAIL'}")
    print(f"  Health Check:   {'✅ PASS' if health_ok else '⚠️  N/A'}")
    print("=" * 60)
    
    if mcp_ok:
        print("\n🎉 Space is operational!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
