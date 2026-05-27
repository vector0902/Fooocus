#!/usr/bin/env python3
"""
Fooocus REST API - Quick Test Script
Tests the basic functionality of the REST API.
"""

import requests
import base64
import sys
from pathlib import Path

API_URL = "http://127.0.0.1:7866"

def test_health():
    """Test health check endpoint"""
    print("\n[1/4] Testing /api/health...")
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "healthy":
            print("[OK] Health check passed")
            return True
        else:
            print(f"[FAIL] Unexpected status: {data}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERR] Cannot connect to API server")
        print("   Make sure Fooocus is running with --enable-api")
        return False
    except Exception as e:
        print(f"[ERR] Error: {e}")
        return False


def test_status():
    """Test status endpoint"""
    print("\n[2/4] Testing /api/status...")
    try:
        response = requests.get(f"{API_URL}/api/status", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        print(f"   Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Uptime: {data.get('uptime', 0):.1f}s")
        print("[OK] Status endpoint working")
        return True
        
    except Exception as e:
        print(f"[ERR] Error: {e}")
        return False


def test_models():
    """Test models listing endpoint"""
    print("\n[3/4] Testing /api/models...")
    try:
        response = requests.get(f"{API_URL}/api/models", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        models = data.get("models", [])
        print(f"   Found {len(models)} models:")
        
        for model in models[:5]:  # Show first 5
            print(f"     - [{model['type']}] {model['name']}")
        
        if len(models) > 5:
            print(f"     ... and {len(models) - 5} more")
        
        print("[OK] Models endpoint working")
        return True
        
    except Exception as e:
        print(f"[ERR] Error: {e}")
        return False


def test_generate():
    """Test image generation endpoint"""
    print("\n[4/4] Testing /api/generate (this may take a while)...")
    
    output_dir = Path("./output/test/")
    output_dir.mkdir(exist_ok=True)
    
    try:
        prompt = "a red apple on a wooden table"
        print(f"   Prompt: '{prompt}'")
        print("   Generating...", end=" ", flush=True)
        
        response = requests.post(
            f"{API_URL}/api/generate",
            json={
                "prompt": prompt,
                "style": "Fooocus V2",
                "steps": 20,
                "seed": 42
            },
            timeout=300  # 5 minutes timeout for generation
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result["success"]:
            images = result.get("images", [])
            
            if images:
                # Save first image
                img_b64 = images[0]
                img_data = base64.b64decode(img_b64.split(",")[1])
                
                output_file = output_dir / "test_apple.png"
                with open(output_file, "wb") as f:
                    f.write(img_data)
                
                print(f"\n   [OK] Image generated successfully!")
                print(f"      Saved to: {output_file}")
                print(f"      Size: {len(img_data) / 1024:.1f} KB")
                print(f"      Time: {result['processing_time']:.2f}s")
                print(f"      Seed: {result['metadata'].get('seed', 'N/A')}")
                return True
            else:
                print("\n[WARN] Generation succeeded but no images returned")
                return False
        else:
            error = result.get("error", "Unknown error")
            print(f"\n[FAIL] Generation failed: {error}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n[TIMEOUT] Request timed out (generation took too long)")
        return False
    except Exception as e:
        print(f"\n[ERR] Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Fooocus REST API Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Health Check", test_health()))
    results.append(("Status", test_status()))
    results.append(("Models", test_models()))
    
    # Only run generation test if other tests passed
    if all(r[1] for r in results):
        results.append(("Generate Image", test_generate()))
    else:
        print("\n[WARN] Skipping generation test (previous tests failed)")
        results.append(("Generate Image", None))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, result in results:
        if result is True:
            status = "[OK] PASS"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        
        print(f"  {name:<20} {status}")
    
    total_passed = sum(1 for _, r in results if r is True)
    total_run = sum(1 for _, r in results if r is not None)
    
    print(f"\nTotal: {total_passed}/{total_run} tests passed")
    
    if total_passed == total_run:
        print("\n[DONE] All tests passed! API is working correctly.")
        return 0
    else:
        print("\n[WARN] Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
