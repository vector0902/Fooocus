#!/usr/bin/env python3
"""
Debug script to check if API arguments are properly parsed
"""
import sys
import os

# Add current directory to path
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)

print(f"Working directory: {os.getcwd()}")
print(f"Script location: {root}")
print(f"Python path includes root: {root in sys.path}")

# Test argument parsing
print("\n" + "="*60)
print("Testing argument parsing...")
print("="*60)

# Simulate command line args
test_args = ['entry_with_update.py', '--always-cpu', '--enable-api']
sys.argv = test_args

print(f"Simulated sys.argv: {sys.argv}")

try:
    from args_manager import args
    
    print(f"\n[OK] Successfully imported args from args_manager")
    print(f"\nChecking API-related attributes:")
    
    print(f"  - hasattr(args, 'enable_api'): {hasattr(args, 'enable_api')}")
    if hasattr(args, 'enable_api'):
        print(f"  - args.enable_api: {args.enable_api}")
    
    print(f"\n  - hasattr(args, 'api_port'): {hasattr(args, 'api_port')}")
    if hasattr(args, 'api_port'):
        print(f"  - args.api_port: {args.api_port}")
    
    print(f"\n  - hasattr(args, 'api_host'): {hasattr(args, 'api_host')}")
    if hasattr(args, 'api_host'):
        print(f"  - args.api_host: {args.api_host}")
    
    # Test the condition used in launch.py
    if hasattr(args, 'enable_api') and args.enable_api:
        print("\n[OK] API should be ENABLED (condition is TRUE)")
    else:
        print("\n[FAIL] API would NOT be enabled (condition is FALSE)")
        
except Exception as e:
    print(f"\n[ERROR] Failed to import or parse args: {e}")
    import traceback
    traceback.print_exc()

# Test if api_server can be imported
print("\n" + "="*60)
print("Testing api_server import...")
print("="*60)

try:
    from api_server import app
    print("[OK] Successfully imported api_server.app")
    print(f"  App title: {app.title}")
except Exception as e:
    print(f"[ERROR] Failed to import api_server: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Diagnostic complete")
print("="*60)
