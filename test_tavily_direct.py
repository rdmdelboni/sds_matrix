#!/usr/bin/env python3
"""Direct test of Tavily API to diagnose 400 errors."""

import httpx
from src.utils.config import TAVILY_CONFIG

def test_tavily_direct():
    """Test Tavily API directly with minimal request."""
    api_key = TAVILY_CONFIG.get("api_key", "")
    base_url = TAVILY_CONFIG.get("base_url", "https://api.tavily.com")
    
    print(f"API Key configured: {bool(api_key)}")
    print(f"API Key length: {len(str(api_key))}")
    print(f"Base URL: {base_url}")
    
    if not api_key:
        print("❌ No API key found!")
        return
    
    # Test 1: Simple search
    print("\n=== Test 1: Simple search ===")
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": "acetone CAS number",
        "max_results": 1,
    }
    
    try:
        with httpx.Client(timeout=30) as client:
            print(f"Sending request to: {base_url}/search")
            print(f"Payload: {payload}")
            response = client.post(f"{base_url}/search", headers=headers, json=payload)
            print(f"Status code: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Results: {len(data.get('results', []))}")
                if 'answer' in data:
                    print(f"Answer: {data['answer']}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response body: {response.text}")
                
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Check API key validity with minimal query
    print("\n=== Test 2: Minimal query ===")
    payload_minimal = {
        "api_key": api_key,
        "query": "test",
    }
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(f"{base_url}/search", headers=headers, json=payload_minimal)
            print(f"Status code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.text}")
            else:
                print("✅ Minimal query succeeded")
                
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Check for rate limiting
    print("\n=== Test 3: API info ===")
    print("Check your Tavily dashboard: https://app.tavily.com/")
    print("Things to verify:")
    print("  - API key is active")
    print("  - Monthly quota not exceeded")
    print("  - No billing issues")

if __name__ == "__main__":
    test_tavily_direct()
