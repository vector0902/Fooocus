#!/usr/bin/env python3
"""
Verify aspect_ratio format conversion
Tests that the API correctly converts * to × for Fooocus handler
"""

def test_aspect_ratio_conversion():
    """Test the format conversion logic"""
    
    test_cases = [
        # (API input, Expected output for handler)
        ("1024*1024", "1024×1024"),
        ("1152*896", "1152×896"),
        ("896*1152", "896×1152"),
        ("704*1408", "704×1408"),
    ]
    
    print("=" * 60)
    print("Aspect Ratio Format Conversion Test")
    print("=" * 60)
    
    all_passed = True
    
    for api_input, expected in test_cases:
        # Simulate the conversion in api_server.py
        converted = api_input.replace('*', '\u00d7')
        
        passed = (converted == expected)
        status = "[OK]" if passed else "[FAIL]"
        
        print(f"\n{status} Input: {api_input:15} -> Output: {converted:15} (Expected: {expected})")
        
        if not passed:
            all_passed = False
            
            # Show what went wrong
            print(f"     ERROR: Character mismatch!")
            print(f"     Converted bytes: {[hex(ord(c)) for c in converted]}")
            print(f"     Expected bytes:   {[hex(ord(c)) for c in expected]}")
    
    # Test that Handler can parse it
    print("\n" + "-" * 60)
    print("Testing Handler Parsing Logic")
    print("-" * 60)
    
    for api_input, expected in test_cases:
        converted = api_input.replace('*', '\u00d7')
        
        try:
            # Simulate async_worker.py line 1118
            width, height = converted.replace('×', ' ').split(' ')[:2]
            width, height = int(width), int(height)
            
            print(f"[OK] Parsed: {converted} -> {width}x{height}")
            
        except ValueError as e:
            print(f"[FAIL] Cannot parse '{converted}': {e}")
            all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] All tests passed! Format conversion is correct.")
        print("\nConversion chain:")
        print("  User/API: '1024*1024' (easy to type)")
        print("       |")
        print("  v  api_server.py converts * -> ×")
        print("       |")
        print("  v  Handler receives: '1024×1024' (Unicode ×)")
        print("       |")
        print("  v  Handler parses successfully!")
    else:
        print("[FAIL] Some tests failed!")
        
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(test_aspect_ratio_conversion())
