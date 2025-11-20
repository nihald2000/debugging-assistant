import modal
import time
from typing import Tuple, Optional

# Define the environment for the sandbox
# We include common data science and utility libraries
sandbox_image = modal.Image.debian_slim().pip_install(
    "numpy", 
    "pandas", 
    "requests", 
    "beautifulsoup4"
)

app = modal.App("debuggenie-sandbox")

class SafeCodeExecutor:
    """
    Executes untrusted code in a secure, isolated Modal Sandbox.
    """
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def execute(self, code: str) -> Tuple[str, str, int]:
        """
        Run Python code in a sandbox and return stdout, stderr, and return code.
        
        Args:
            code: The Python code to execute.
            
        Returns:
            Tuple[str, str, int]: (stdout, stderr, return_code)
        """
        print(f"[*] Spawning Modal Sandbox for code execution (timeout={self.timeout}s)...")
        
        try:
            # Create the sandbox container
            # We run python -c "code"
            sandbox = modal.Sandbox.create(
                "python", "-c", code,
                image=sandbox_image,
                app=app,
                timeout=self.timeout,
                cpu=1.0,
                memory=1024  # 1GB limit
            )
            
            # Wait for completion
            sandbox.wait()
            
            # Capture Output
            stdout = sandbox.stdout.read()
            stderr = sandbox.stderr.read()
            return_code = sandbox.returncode
            
            return stdout, stderr, return_code

        except Exception as e:
            return "", f"Sandbox execution failed: {str(e)}", -1

if __name__ == "__main__":
    # Example Usage
    executor = SafeCodeExecutor()
    
    unsafe_code = """
import os
import numpy as np

print(f"Running in: {os.getcwd()}")
print(f"Random number: {np.random.random()}")
# Attempt to access sensitive file (should fail or be isolated)
try:
    with open("/etc/shadow", "r") as f:
        print(f.read())
except Exception as e:
    print(f"Security check passed: {e}")
"""
    
    # Note: To run this locally, you need 'modal setup' configured
    with app.run():
        out, err, rc = executor.execute(unsafe_code)
        print(f"Return Code: {rc}")
        print(f"Stdout:\n{out}")
        print(f"Stderr:\n{err}")
