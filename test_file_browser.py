#!/usr/bin/env python3
"""
Test the file browser functionality
"""

import requests
import json
import sys

API_URL = "http://127.0.0.1:7866"

print("=" * 70)
print("Testing File Browser Functionality")
print("=" * 70)

# Test 1: List files API
print("\n[TEST 1] File Listing API (/api/files)")
try:
    response = requests.get(f"{API_URL}/api/files", timeout=10)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Path: {data.get('path')}")
        print(f"  Files: {data.get('total_files', 0)}")
        print(f"  Directories: {data.get('total_dirs', 0)}")
        print(f"  Total Size: {data.get('total_size', 0)} bytes")
        
        if data.get('items'):
            print(f"\n  Items (first 5):")
            for item in data['items'][:5]:
                icon = "[DIR]" if item['type'] == 'directory' else "[FILE]"
                size = f" ({item['size']} bytes)" if item['size'] else ""
                print(f"    {icon} {item['name']}{size}")
            
            if len(data['items']) > 5:
                print(f"    ... and {len(data['items']) - 5} more")
        
        print("  [OK] File listing works!")
    else:
        print(f"  [FAIL] Error: {response.text}")
        
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 2: Direct file access endpoint info
print("\n[TEST 2] Static Files Endpoint Info")
print(f"  Base URL: {API_URL}/files/")
print(f"  Example: {API_URL}/files/<filename>")
print("  [INFO] Files can be accessed directly via /files/ path")

# Test 3: Browser UI endpoint
print("\n[TEST 3] Browser UI Endpoint (/api/browser)")
try:
    response = requests.get(f"{API_URL}/api/browser", timeout=10)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            print(f"  Content-Type: {content_type}")
            print(f"  Content Length: {len(response.text)} bytes")
            print("  [OK] Browser UI is accessible!")
            print(f"\n  Open in browser: {API_URL}/api/browser")
        else:
            print(f"  [WARN] Unexpected content type: {content_type}")
    else:
        print(f"  [FAIL] Error: {response.text}")
        
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 4: Create test file and verify access
print("\n[TEST 4] Create Test File & Verify Access")
try:
    import os
    from pathlib import Path
    
    # Create a simple test file in output directory
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    
    test_file = output_dir / "browser_test.txt"
    with open(test_file, 'w') as f:
        f.write("File browser test - created at " + __import__('datetime').datetime.now().isoformat())
    
    print(f"  Created test file: {test_file}")
    
    # Try to access it via /files/ endpoint
    file_url = f"{API_URL}/files/{test_file.name}"
    print(f"  Attempting to access: {file_url}")
    
    response = requests.get(file_url, timeout=10)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"  Content-Length: {len(response.content)} bytes")
        print(f"  Content preview: {response.text[:50]}...")
        print("  [OK] Direct file access works!")
    elif response.status_code == 404:
        print("  [WARN] File not found (may need to check path)")
    else:
        print(f"  [WARN] Status: {response.status_code}")
    
    # Clean up test file
    test_file.unlink()
    print(f"  Cleaned up test file")
    
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("[DONE] File browser tests completed!")
print("\nUsage:")
print(f"  1. Browse files: Open http://127.0.0.1:7866/api/browser in browser")
print(f"  2. List files via API: GET {API_URL}/api/files")
print(f"  3. Direct file access: GET {API_URL}/files/<filename>")
print("=" * 70)
