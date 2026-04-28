"""
Tests for parse_cap_meta() - CrysAlisPro experiment metadata extraction.
Tests both single experiments and CSV results files.
"""
from cap_auto.cap_files import parse_cap_meta
import pprint
import os

print("=" * 80)
print("parse_cap_meta() Tests")
print("=" * 80)

# Test 1: Single experiment directory
print("\nTest 1: Parsing single experiment directory")
print("-" * 80)

info_single = parse_cap_meta('example_data\\exp_11317')
if info_single:
    print(f"✓ Parsed metadata for {len(info_single)} experiment(s)")
    exp = info_single[0]
    print(f"\nExperiment details:")
    print(f"  Name: {exp.get('name', 'N/A')}")
    print(f"  Digest: {exp.get('digest', 'N/A')}")
    print(f"  R_int: {exp.get('r_int', 'N/A')}")
    print(f"  Indexation: {exp.get('indexation', 'N/A')}")
    print(f"  Collection time: {exp.get('collection_time', 'N/A')}")
    print(f"  Wavelength: {exp.get('wavelength', 'N/A')} Å")
    print(f"  Temperature: {exp.get('temperature', 'N/A')} K")
    
    # Check for required fields
    required_fields = ['name', 'digest']
    missing = [f for f in required_fields if f not in exp]
    if missing:
        print(f"\n⚠ Missing required fields: {missing}")
    else:
        print(f"\n✓ All required fields present")
else:
    print("✗ Failed to parse metadata")

print("\nFull metadata:")
pprint.pprint(info_single)

# Test 2: CSV results file (if available)
print("\n" + "=" * 80)
print("Test 2: Parsing CSV results file")
print("-" * 80)

csv_path = 'example_data\\trehalose_results.csv'
if os.path.exists(csv_path):
    info_multiple = parse_cap_meta(csv_path)
    if info_multiple:
        print(f"✓ Parsed metadata for {len(info_multiple)} experiment(s) from CSV")
        
        # Show first few entries
        for i, exp in enumerate(info_multiple[:3]):
            print(f"\nExperiment {i+1}:")
            print(f"  Name: {exp.get('name', 'N/A')}")
            print(f"  R_int: {exp.get('r_int', 'N/A')}")
            print(f"  Indexation: {exp.get('indexation', 'N/A')}")
        
        if len(info_multiple) > 3:
            print(f"\n... and {len(info_multiple) - 3} more experiments")
    else:
        print("✗ Failed to parse CSV metadata")
else:
    print(f"⊘ CSV file not found: {csv_path}")
    print("  Skipping CSV test")

# Test 3: Still scans (if available)
print("\n" + "=" * 80)
print("Test 3: Parsing still scan metadata (optional)")
print("-" * 80)

still_path = 'C:\\XcaliburData\\first_still_run\\grid 2'
if os.path.exists(still_path):
    info_still = parse_cap_meta(still_path)
    if info_still:
        print(f"✓ Parsed metadata for {len(info_still)} still scan(s)")
        exp = info_still[0]
        print(f"  Name: {exp.get('name', 'N/A')}")
        print(f"  Collection type: {exp.get('collection_type', 'N/A')}")
    else:
        print("✗ Failed to parse still scan metadata")
else:
    print(f"⊘ Still scan path not found: {still_path}")
    print("  Skipping still scan test")

# Test 4: Edge cases - missing files
print("\n" + "=" * 80)
print("Test 4: Edge cases - missing/invalid paths")
print("-" * 80)

# Test with non-existent path
try:
    info_missing = parse_cap_meta('nonexistent_path')
    print(f"✓ Non-existent path handled: returned {len(info_missing)} experiments")
except FileNotFoundError:
    print(f"✓ Non-existent path correctly raised FileNotFoundError")

# Test with empty path
try:
    info_empty = parse_cap_meta('')
    print(f"✓ Empty path handled: returned {len(info_empty)} experiments")
except (FileNotFoundError, ValueError) as e:
    print(f"✓ Empty path correctly raised exception: {type(e).__name__}")

# Test 5: Test include_merged parameter
print("\n" + "=" * 80)
print("Test 5: Testing include_merged parameter")
print("-" * 80)

info_no_merged = parse_cap_meta('example_data\\exp_11317', include_merged=False)
print(f"✓ include_merged=False: {len(info_no_merged)} experiment(s)")

info_with_merged = parse_cap_meta('example_data\\exp_11317', include_merged=True)
print(f"✓ include_merged=True: {len(info_with_merged)} experiment(s)")

# Test 6: Test exclude parameter
print("\n" + "=" * 80)
print("Test 6: Testing exclude parameter")
print("-" * 80)

# Exclude experiments with specific patterns
info_excluded = parse_cap_meta('example_data\\exp_11317', exclude=('auto', 'merged'))
print(f"✓ Excluded 'auto' and 'merged': {len(info_excluded)} experiment(s)")

# Test 7: Verify expected values for known test data
print("\n" + "=" * 80)
print("Test 7: Verifying expected values for test data")
print("-" * 80)

if info_single:
    exp = info_single[0]
    
    # Check expected name pattern
    if 'exp_11317' in exp.get('name', ''):
        print(f"✓ Name matches expected pattern: {exp['name']}")
    else:
        print(f"⚠ Name doesn't match expected pattern: {exp.get('name', 'N/A')}")
    
    # Check digest exists and is reasonable length
    digest = exp.get('digest', '')
    if digest and len(digest) > 10:
        print(f"✓ Digest appears valid: {digest[:20]}... (length: {len(digest)})")
    else:
        print(f"⚠ Digest may be invalid: {digest}")
    
    # Check numeric fields are actually numeric
    numeric_fields = ['r_int', 'wavelength', 'temperature']
    for field in numeric_fields:
        if field in exp:
            try:
                float(exp[field])
                print(f"✓ {field} is numeric: {exp[field]}")
            except (ValueError, TypeError):
                print(f"⚠ {field} is not numeric: {exp[field]}")

print("\n" + "=" * 80)
print("All parse_cap_meta() tests completed!")
print("=" * 80)

# TODO: Future enhancements
# - Test queued collections vs single experiments
# - Test rotation scans vs still scans explicitly
# - Test different file format versions
# - Test merged vs non-merged experiment filtering
# - Test with corrupted/malformed metadata files
