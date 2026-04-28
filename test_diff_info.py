"""
Comprehensive tests for diffraction data parsing and analysis.
Tests the new refactored API that returns List[Dict] instead of pandas DataFrames.
"""
from cap_auto.cap_files import (
    parse_reflection_table,
    parse_powder_pattern,
    DiffractionData,
    generate_powder_commands,
    generate_reflection_commands,
    get_diff_info,
    parse_cap_meta
)
from cap_auto.cap_control import CAPInstance
import pprint
import os

# Test 1: Parse existing files without CAP
print("=" * 80)
print("Test 1: Parsing existing diffraction files")
print("=" * 80)

exp_path = 'example_data\\exp_11317\\exp_11317'
tab_file = exp_path + '.tab'
dat_file = 'example_data\\exp_11317\\radial.dat'

# Parse reflection table
reflections, refl_cmds = parse_reflection_table(tab_file, wavelength=0.0251)
print(f"\n✓ Parsed {len(reflections)} reflections from {os.path.basename(tab_file)}")
if reflections:
    print(f"  First reflection: d = {reflections[0]['d']:.3f} Å, I = {reflections[0]['I']:.1f}")
    print(f"  Last reflection: d = {reflections[-1]['d']:.3f} Å, I = {reflections[-1]['I']:.1f}")
print(f"  Commands to generate: {refl_cmds}")

# Parse powder pattern
powder, powder_cmds = parse_powder_pattern(dat_file)
print(f"\n✓ Parsed {len(powder)} powder points from {os.path.basename(dat_file)}")
if powder:
    print(f"  d-spacing range: {powder[0]['d_value']:.2f} - {powder[-1]['d_value']:.2f} Å")
    print(f"  Total intensity: {sum(p['intensity'] for p in powder):.1f}")
print(f"  Commands to generate: {powder_cmds}")

# Test 2: DiffractionData class with auto shell boundaries
print("\n" + "=" * 80)
print("Test 2: DiffractionData class with auto-suggested shells")
print("=" * 80)

diff_data = DiffractionData(reflections, powder, wavelength=0.0251)

# Compute shells with auto-suggestion
shells = diff_data.compute_shell_statistics()
print(f"\n✓ Computed statistics for {len(shells)} shells (auto-suggested boundaries)")
print("\nShell statistics:")
print(f"{'d_max':>8} {'d_min':>8} {'N_peaks':>8} {'I_peak':>12} {'I_tot':>12} {'ratio':>8}")
print("-" * 70)
for shell in shells:
    d_max = shell['d_max'] if shell['d_max'] != float('inf') else 999.9
    print(f"{d_max:8.2f} {shell['d_min']:8.2f} {shell['N_peaks']:8d} "
          f"{shell['I_peak']:12.1f} {shell['I_tot']:12.1f} {shell['peak_ratio']:8.3f}")

# Test 3: Custom shell boundaries
print("\n" + "=" * 80)
print("Test 3: DiffractionData with custom shell boundaries")
print("=" * 80)

custom_boundaries = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]  # in 1/Å
shells_custom = diff_data.compute_shell_statistics(shell_boundaries=custom_boundaries)
print(f"\n✓ Computed statistics for {len(shells_custom)} custom shells")
print(f"  Boundaries (1/Å): {custom_boundaries}")

# Test 4: Generate CAP commands (without executing)
print("\n" + "=" * 80)
print("Test 4: CAP command generation")
print("=" * 80)

powder_cmds = generate_powder_commands(exp_path, wavelength=0.0251, d_min=0.3, d_max=20.0)
print(f"\n✓ Powder generation commands:")
for cmd in powder_cmds:
    print(f"  {cmd}")

refl_cmds = generate_reflection_commands(exp_path, redo_peak_hunt=True)
print(f"\n✓ Reflection generation commands:")
for cmd in refl_cmds:
    print(f"  {cmd}")

# Test 5: Parse missing file (should return empty with warning)
print("\n" + "=" * 80)
print("Test 5: Parsing non-existent files (should warn)")
print("=" * 80)

missing_reflections, _ = parse_reflection_table('nonexistent.tab')
print(f"\n✓ Parsing missing file returned {len(missing_reflections)} reflections (expected 0)")

missing_powder, _ = parse_powder_pattern('nonexistent.dat')
print(f"✓ Parsing missing file returned {len(missing_powder)} powder points (expected 0)")

# Test 6: Integration test with metadata
print("\n" + "=" * 80)
print("Test 6: Integration with metadata parsing")
print("=" * 80)

meta = parse_cap_meta('example_data\\exp_11317')
if meta:
    exp = meta[0]
    print(f"\n✓ Parsed metadata for: {exp['name']}")
    print(f"  R_int: {exp.get('r_int', 'N/A')}")
    print(f"  Indexation: {exp.get('indexation', 'N/A')}")
    print(f"  Digest: {exp['digest']}")

# Test 7: Full get_diff_info without CAP (parsing only)
print("\n" + "=" * 80)
print("Test 7: get_diff_info() without CAP instance (parse existing files)")
print("=" * 80)

shells_full, refl_full, powder_full, img_path = get_diff_info(
    exp_path,
    cap=None,  # No CAP - just parse existing files
    keep_peak_file=True,
    keep_powder_file=True,
    wavelength=0.0251
)

print(f"\n✓ Parsed {len(refl_full)} reflections and {len(powder_full)} powder points")
print(f"✓ Computed {len(shells_full)} shells")
print(f"  Diff image path: {img_path}")

# Test 8: Summary statistics
print("\n" + "=" * 80)
print("Test 8: Summary statistics")
print("=" * 80)

if reflections:
    d_spacings = [r['d'] for r in reflections if r['d'] > 0]
    intensities = [r['I'] for r in reflections]
    print(f"\nReflection statistics:")
    print(f"  Count: {len(reflections)}")
    print(f"  d-spacing range: {min(d_spacings):.3f} - {max(d_spacings):.3f} Å")
    print(f"  Intensity range: {min(intensities):.1f} - {max(intensities):.1f}")
    print(f"  Mean intensity: {sum(intensities) / len(intensities):.1f}")

if powder:
    print(f"\nPowder pattern statistics:")
    print(f"  Count: {len(powder)}")
    print(f"  Total integrated intensity: {sum(p['intensity'] for p in powder):.1f}")
    print(f"  Mean count per bin: {sum(p['count'] for p in powder) / len(powder):.1f}")

print("\n" + "=" * 80)
print("All tests completed!")
print("=" * 80)

# Optional: Test with CAP if available (commented out by default)
"""
print("\n" + "=" * 80)
print("Test 9: Full workflow with CAP instance (optional)")
print("=" * 80)

# Uncomment to test with real CAP instance
# cap = CAPInstance(start_now=True, min_cap_version='45.50')
# try:
#     shells, refl, powder, img = get_diff_info(
#         exp_path,
#         cap=cap,
#         redo_peak_hunt=False,
#         keep_peak_file=False,
#         keep_powder_file=False
#     )
#     print(f"✓ Generated and parsed files via CAP")
#     print(f"  Reflections: {len(refl)}, Powder points: {len(powder)}, Shells: {len(shells)}")
# finally:
#     cap.stop()
"""