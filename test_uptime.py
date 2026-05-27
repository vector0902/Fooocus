#!/usr/bin/env python3
"""
Test the /api/uptime endpoint
"""

import requests
import json
import sys

API_URL = "http://127.0.0.1:7866"

print("=" * 70)
print("Testing /api/uptime Endpoint")
print("=" * 70)

try:
    print("\n[GET] http://127.0.0.1:7866/api/uptime")
    response = requests.get(f"{API_URL}/api/uptime", timeout=10)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\n" + "-" * 70)
        print("System Information (Formatted)")
        print("-" * 70)
        
        # System info
        if 'system' in data:
            sys_info = data['system']
            print(f"\n[SYSTEM]")
            print(f"  Hostname:      {sys_info.get('hostname', 'N/A')}")
            print(f"  Uptime:        {sys_info.get('uptime_human', 'N/A')}")
            print(f"  Boot Time:     {sys_info.get('boot_time', 'N/A')}")
            print(f"  Platform:      {sys_info.get('platform', 'N/A')[:60]}...")
            print(f"  Python:        {sys_info.get('python_version', 'N/A')}")
        
        # CPU info
        if 'cpu' in data:
            cpu = data['cpu']
            print(f"\n[CPU]")
            print(f"  Usage:         {cpu.get('usage_percent', 'N/A')}%")
            print(f"  Cores (logical): {cpu.get('logical_cores', 'N/A')}")
            print(f"  Cores (physical): {cpu.get('physical_cores', 'N/A')}")
            
            load_avg = cpu.get('load_average', {})
            if load_avg:
                print(f"  Load Average:")
                print(f"    1 min:   {load_avg.get('1min', 'N/A')}")
                print(f"    5 min:   {load_avg.get('5min', 'N/A')}")
                print(f"    15 min:  {load_avg.get('15min', 'N/A')}")
        
        # Memory info
        if 'memory' in data:
            mem = data['memory']
            print(f"\n[MEMORY]")
            print(f"  Total:    {mem.get('total_gb', 'N/A')} GB")
            print(f"  Used:     {mem.get('used_gb', 'N/A')} GB ({mem.get('percent', 'N/A')}%)")
            print(f"  Available:{mem.get('available_gb', 'N/A')} GB")
        
        # Swap info (if available)
        if 'swap' in data:
            swap = data['swap']
            if swap.get('total_gb', 0) > 0:
                print(f"\n[SWAP]")
                print(f"  Total: {swap['total_gb']} GB")
                print(f"  Used:  {swap['used_gb']} GB ({swap['percent']}%)")
        
        # Disk info
        if 'disk' in data:
            disk = data['disk']
            print(f"\n[DISK (/)]")
            print(f"  Total: {disk.get('total_gb', 'N/A')} GB")
            print(f"  Used:  {disk.get('used_gb', 'N/A')} GB ({disk.get('percent', 'N/A')}%)")
            print(f"  Free:  {disk.get('free_gb', 'N/A')} GB")
        
        # GPU info (if available)
        if 'gpu' in data and data['gpu']:
            gpu = data['gpu']
            print(f"\n[GPU]")
            print(f"  Name:           {gpu.get('name', 'N/A')}")
            print(f"  Memory:         {gpu.get('memory_used_mb', 'N/A')} MB / {gpu.get('memory_total_mb', 'N/A')} MB")
            print(f"  Load:           {gpu.get('load', 'N/A')}")
            print(f"  Temperature:    {gpu.get('temperature', 'N/A')}")
        else:
            print("\n[GPU] Not detected or psutil/GPU not installed")
        
        # Fooocus process info
        if 'fooocus_process' in data:
            proc = data['fooocus_process']
            print(f"\n[FOOCUS PROCESS]")
            print(f"  PID:          {proc.get('pid', 'N/A')}")
            print(f"  Memory Usage: {proc.get('memory_mb', 'N/A')} MB")
            print(f"  CPU Usage:    {proc.get('cpu_percent', 'N/A')}%")
            print(f"  Threads:      {proc.get('num_threads', 'N/A')}")
            print(f"  Started:      {proc.get('create_time', 'N/A')}")
        
        print("\n" + "-" * 70)
        print("[OK] /api/uptime endpoint working correctly!")
        print("-" * 70)
        
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
