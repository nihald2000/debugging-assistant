#!/usr/bin/env python3
"""
DebugGenie Quick Start Script
Checks setup and launches the application
"""

import sys
import os
from pathlib import Path

def print_header():
    print("\n" + "="*60)
    print("  🧞 DebugGenie - AI Debugging Assistant")
    print("="*60 + "\n")

def check_python_version():
    """Ensure Python 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        print(f"   Current: Python {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")

def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    if in_venv:
        print("✅ Virtual environment active")
    else:
        print("⚠️  Not in virtual environment (recommended)")
        print("   Run: python -m venv venv")
        print("   Then: venv\\Scripts\\activate  (Windows)")
        print("   Or:   source venv/bin/activate  (Unix)")

def check_packages():
    """Check if critical packages are installed"""
    required = [
        ('gradio', 'gradio'),
        ('anthropic', 'anthropic'),
        ('google.generativeai', 'google-generativeai'),
        ('openai', 'openai'),
        ('loguru', 'loguru'),
        ('plotly', 'plotly'),
    ]
    
    missing = []
    for import_name, package_name in required:
        try:
            __import__(import_name.split('.')[0])
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name}")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️  Missing packages detected")
        print("   Run: pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """Check if .env exists"""
    env_path = Path('.env')
    if env_path.exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found")
        print("   Copy .env.example to .env and add your API keys")
        print("   Required: ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY, OPENAI_API_KEY")
        return False

def check_api_keys():
    """Check if API keys are set"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        keys = {
            'ANTHROPIC_API_KEY': 'Anthropic (Claude)',
            'GOOGLE_AI_API_KEY': 'Google AI (Gemini)',
            'OPENAI_API_KEY': 'OpenAI (GPT-4)',
        }
        
        all_set = True
        for key, name in keys.items():
            if os.getenv(key):
                print(f"✅ {name}")
            else:
                print(f"❌ {name}")
                all_set = False
        
        # Optional keys
        if os.getenv('ELEVENLABS_API_KEY'):
            print("✅ ElevenLabs (Voice) - Optional")
        else:
            print("⚠️  ElevenLabs (Voice) - Optional, not set")
        
        return all_set
    except ImportError:
        print("❌ python-dotenv not installed")
        return False

def show_quick_start():
    """Show quick start instructions"""
    print("\n" + "="*60)
    print("  Quick Start Guide")
    print("="*60)
    print("""
1. Install dependencies (if not done):
   pip install -r requirements.txt

2. Configure API keys:
   - Copy .env.example to .env
   - Add your API keys to .env

3. Run the application:
   python app.py

4. Open browser:
   http://localhost:7860

For detailed setup, see SETUP.md
    """)

def launch_app():
    """Launch the application"""
    print("\n" + "="*60)
    print("  Launching DebugGenie...")
    print("="*60 + "\n")
    
    try:
        import app
        app.main()
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Failed to launch: {e}")
        print("\nCheck SETUP.md for troubleshooting")
        sys.exit(1)

def main():
    print_header()
    
    print("Checking setup...\n")
    
    # Run checks
    check_python_version()
    check_venv()
    packages_ok = check_packages()
    env_ok = check_env_file()
    
    if not packages_ok:
        show_quick_start()
        sys.exit(1)
    
    if env_ok:
        print("\nChecking API keys...\n")
        keys_ok = check_api_keys()
        
        if not keys_ok:
            print("\n⚠️  Some API keys are missing")
            print("   The app may run in limited mode")
            print("   Add keys to .env for full functionality\n")
    
    # Ask to launch
    print("\n" + "="*60)
    response = input("Launch DebugGenie? (y/n): ").lower()
    
    if response == 'y':
        launch_app()
    else:
        print("\n✋ Launch cancelled")
        show_quick_start()

if __name__ == "__main__":
    main()
