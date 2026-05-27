#!/usr/bin/env python3
"""
Test the updated /api/uptime endpoint with accurate instance uptime
"""

import requests
import json
import sys

API_URL = "http://127.0.0.1:7866"

print("=" * 70)
print("Testing /api/uptime - Instance Uptime Endpoint")
print("=" * 70)

try:
    print("\n[GET] http://127.0.0.1:7866/api/uptime")
    response = requests.get(f"{API_URL}/api/uptime", timeout=10)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\n" + "-" * 70)
        print("INSTANCE UPTIME (Primary - What You Need)")
        print("-" * 70)
        
        # Instance uptime (the main thing)
        if 'instance' in data:
            inst = data['instance']
            print(f"\n[Fooocus Instance]")
            print(f"  Uptime:         {inst.get('uptime_human', 'N/A')}")
            print(f"  Uptime (exact): {inst.get('uptime_seconds', 'N/A')} seconds")
            print(f"  Started at:     {inst.get('start_time', 'N/A')}")
            print(f"  PID:            {inst.get('pid', 'N/A')}")
        
        # Session countdown (for temporary instances)
        if 'session' in data:
            sess = data['session']
            print(f"\n[Session Countdown] (Temporary Instance)")
            print(f"  Max Duration:   {sess.get('max_duration_human', 'N/A')}")
            print(f"  Elapsed:        {sess.get('elapsed_human', 'N/A')} ({sess.get('usage_percent', 0)}% used)")
            print(f"  Remaining:      {sess.get('remaining_human', 'N/A')}")
            
            if sess.get('is_expiring_soon'):
                print("  *** WARNING: Session expiring soon (< 60s)! ***")
            if sess.get('expired'):
                print("  *** ERROR: Session has EXPIRED! ***")
        else:
            print("\n[Session Countdown] Not configured")
            print("  To enable, set MAX_SESSION_DURATION in api_server.py")
        
        # System resources (secondary info)
        if 'resources' in data:
            res = data['resources']
            print(f"\n[System Resources]")
            print(f"  CPU Usage:      {res.get('cpu_percent', 'N/A')}%")
            
            mem = res.get('memory', {})
            if mem:
                print(f"  Memory:         {mem.get('used_gb', 'N/A')} GB / {mem.get('total_gb', 'N/A')} GB ({mem.get('percent', 'N/A')}%)")
            
            proc = res.get('process', {})
            if proc:
                print(f"  Process Memory: {proc.get('memory_mb', 'N/A')} MB")
                print(f"  Process CPU:    {proc.get('cpu_percent', 'N/A')}%")
        
        # GPU info
        if 'gpu' in data:
            gpu = data['gpu']
            print(f"\n[GPU]")
            print(f"  Model:          {gpu.get('name', 'N/A')}")
            print(f"  Memory Used:    {gpu.get('memory_used_mb', 'N/A')} MB / {gpu.get('memory_total_mb', 'N/A')} MB")
            print(f"  Load:           {gpu.get('load', 'N/A')}")
        
        print("\n" + "-" * 70)
        print("[OK] /api/uptime endpoint working correctly!")
        print("-" * 70)
        print("\nNOTE: This shows FOOOCUS INSTANCE uptime, NOT system uptime.")
        print("      This is the time since the API server started.")
        
        # Option to show raw JSON
        if len(sys.argv) > 1 and sys.argv[1] == '--json':
            print("\n\nRaw JSON Response:")
            print(json.dumps(data, indent=2))
        
    else:
        print(f"[ERROR] HTTP {response.status_code}: {response.text}")
        sys.exit(1)

except requests.exceptions.ConnectionError:
    print("[ERROR] Cannot connect to API server")
    print("       Make sure Fooocus is running with --enable-api")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
