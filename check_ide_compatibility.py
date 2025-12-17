import subprocess
import sys
import time
import os

def check_stdio_compatibility():
    print("🔍 Checking MCP Server Stdio Compatibility...")
    
    # Command to run the MCP server in stdio mode via Docker
    # We assume the container is running or at least the image exists
    cmd = [
        "docker", "exec", "-i", 
        "-e", "TRANSPORT=stdio", 
        "archon-mcp", 
        "python", "-m", "src.mcp_server.mcp_server"
    ]
    
    print(f"🚀 Running command: {' '.join(cmd)}")
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        print("✅ Process started. Waiting for initialization...")
        time.sleep(2)
        
        if process.poll() is not None:
            print("❌ Process exited prematurely!")
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return False
            
        print("✅ Process is running. Simulating IDE disconnect (closing stdin)...")
        
        # Close stdin to simulate IDE disconnect
        process.stdin.close()
        
        # Wait for process to exit
        stdout, stderr = process.communicate(timeout=5)
        
        print("✅ Process exited.")
        
        # Check for the specific error in stderr
        if "ValueError('I/O operation on closed file.')" in stderr or "lost sys.stderr" in stderr:
            print("❌ FAILED: Found 'I/O operation on closed file' error in stderr.")
            print("STDERR Output:\n", stderr)
            return False
            
        print("✅ SUCCESS: No 'closed file' errors found in stderr.")
        if stderr:
            print("ℹ️  STDERR Output (Clean):\n", stderr)
            
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout waiting for process to exit.")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

if __name__ == "__main__":
    success = check_stdio_compatibility()
    sys.exit(0 if success else 1)
