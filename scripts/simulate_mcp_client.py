import asyncio
import httpx
import sys
import signal

async def simulate_client():
    url = "http://localhost:8051/sse"
    print(f"Connecting to {url}...")
    
    headers = {
        "User-Agent": "SimulatedClient/1.0 (Test)"
    }
    
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, headers=headers) as response:
                print("Connected! Keeping connection open...")
                print("Press Ctrl+C to stop.")
                
                async for line in response.aiter_lines():
                    if line:
                        print(f"Received: {line}")
                        
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_client())
    except KeyboardInterrupt:
        print("\nStopped.")
