#!/usr/bin/env python3
"""
Quick test for the fixed Fooocus API generation
Run this on the remote server after updating api_server.py
"""

import requests
import sys
import time

API_URL = "http://127.0.0.1:7866"

print("=" * 60)
print("Testing Fixed Fooocus API Generation")
print("=" * 60)

# Test health first
print("\n[1] Checking API health...")
try:
    response = requests.get(f"{API_URL}/api/health", timeout=5)
    if response.status_code == 200:
        print("    [OK] API is running")
    else:
        print(f"    [FAIL] Status: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"    [ERROR] {e}")
    sys.exit(1)

# Test generation
print("\n[2] Testing image generation (this may take 1-2 minutes)...")
print("    Prompt: 'a red apple on a wooden table'")

start_time = time.time()

try:
    payload = {
        "prompt": "a red apple on a wooden table",
        "style": "Fooocus V2",
        "steps": 20,
        "seed": 42
    }
    
    print("    Sending request...")
    response = requests.post(
        f"{API_URL}/api/generate",
        json=payload,
        timeout=300
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n    Response status: {response.status_code}")
    print(f"    Time elapsed: {elapsed:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get("success"):
            images = result.get("images", [])
            print(f"\n    [SUCCESS] Image generated!")
            print(f"    Images: {len(images)}")
            print(f"    Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"    Seed: {result.get('metadata', {}).get('seed', 'N/A')}")
            
            # Save image
            if images:
                import base64
                from pathlib import Path
                
                output_dir = Path("./test_output")
                output_dir.mkdir(exist_ok=True)
                
                img_b64 = images[0]
                img_data = base64.b64decode(img_b64.split(",")[1])
                
                output_file = output_dir / "fixed_test.png"
                with open(output_file, "wb") as f:
                    f.write(img_data)
                
                print(f"    Saved to: {output_file}")
                print(f"    Size: {len(img_data)/1024:.1f} KB")
            
            print("\n" + "=" * 60)
            print("[DONE] All tests passed! API is working correctly.")
            print("=" * 60)
        else:
            error = result.get("error", "Unknown error")
            print(f"\n    [FAIL] Generation failed: {error}")
            print("\n" + "=" * 60)
            print("[WARN] Generation failed. Check error message above.")
            print("=" * 60)
            sys.exit(1)
    else:
        print(f"\n    [FAIL] HTTP Error: {response.text}")
        sys.exit(1)
        
except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n    [ERROR] {e}")
    print(f"    Time elapsed: {elapsed:.2f}s")
    import traceback
    traceback.print_exc()
    sys.exit(1)
