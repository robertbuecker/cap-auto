"""
Tests for ProffitXML class - CrysAlisPro data reduction parameter XML handler.
"""
from cap_auto.cap_files import ProffitXML
import os
import shutil
import tempfile

# Test file paths
TEST_DATA_DIR = 'example_data\\exp_11317'
TEST_XML = os.path.join(TEST_DATA_DIR, 'exp_11317.xml')

print("=" * 80)
print("ProffitXML Tests")
print("=" * 80)

# Test 1: Load existing XML file
print("\nTest 1: Loading existing Proffit XML")
print("-" * 80)

proffit = ProffitXML('exp_11317.xml', path=TEST_DATA_DIR, parse=True)
print(f"✓ Loaded XML from: {TEST_XML}")
print(f"  Exists: {os.path.exists(TEST_XML)}")

# Test 2: Read key parameters
print("\nTest 2: Reading key parameters from XML")
print("-" * 80)

# Access internal parsed data (implementation detail - may need adjustment)
if hasattr(proffit, 'tree') and proffit.tree is not None:
    root = proffit.tree.getroot()
    
    # Find key parameters
    params = root.find('__PROFFIT__PARAMETERS__')
    if params is not None:
        laue = params.find('__Type_of_Laue__')
        dmin = params.find('__dmin__')
        dmax = params.find('__dmax__')
        gral = params.find('__Gral_mode__')
        friedel = params.find('__Is_Friedel_mate_on__')
        scan_width = params.find('__Scan_width_in_deg__')
        
        print(f"  Laue symmetry: {laue.text if laue is not None else 'N/A'}")
        print(f"  d_min: {dmin.text if dmin is not None else 'N/A'} Å")
        print(f"  d_max: {dmax.text if dmax is not None else 'N/A'} Å")
        print(f"  GRAL mode: {gral.text if gral is not None else 'N/A'}")
        print(f"  Friedel mates: {friedel.text if friedel is not None else 'N/A'}")
        print(f"  Scan width: {scan_width.text if scan_width is not None else 'N/A'}°")
    else:
        print("  Warning: Could not find __PROFFIT__PARAMETERS__ section")
    
    # Check AutoChem section
    autochem_section = root.find('__AUTOCHEM__SETTING__SECTION__')
    if autochem_section is not None:
        ac_enabled = autochem_section.find('__default_AC_script__')
        print(f"  AutoChem script: {ac_enabled.text if ac_enabled is not None else 'N/A'}")
else:
    print("  Warning: XML not parsed or tree not available")

# Test 3: Create temporary copy and modify parameters
print("\nTest 3: Modifying parameters via set_parameters()")
print("-" * 80)

# Create temporary directory for test
with tempfile.TemporaryDirectory() as tmpdir:
    test_xml_copy = os.path.join(tmpdir, 'test_proffit.xml')
    shutil.copy(TEST_XML, test_xml_copy)
    
    # Load copy
    proffit_mod = ProffitXML('test_proffit.xml', path=tmpdir, parse=True)
    
    # Modify key parameters
    proffit_mod.set_parameters(
        laue=3,  # Change Laue symmetry
        d_min=0.6,  # Change resolution limits
        d_max=50.0,
        scan_width=1.5,  # Change scan width
        friedel_mates=False,  # Disable Friedel mates
        gral_mode=2,  # Manual GRAL mode
        autochem=True  # Enable AutoChem
    )
    
    print(f"✓ Modified parameters and saved to: {test_xml_copy}")
    
    # Reload and verify changes
    proffit_verify = ProffitXML('test_proffit.xml', path=tmpdir, parse=True)
    if proffit_verify.tree is not None:
        root = proffit_verify.tree.getroot()
        params = root.find('__PROFFIT__PARAMETERS__')
        
        if params is not None:
            laue = params.find('__Type_of_Laue__')
            dmin = params.find('__dmin__')
            dmax = params.find('__dmax__')
            scan_width = params.find('__Scan_width_in_deg__')
            friedel = params.find('__Is_Friedel_mate_on__')
            gral = params.find('__Gral_mode__')
            
            print(f"  Verified Laue: {laue.text if laue is not None else 'N/A'} (expected 3)")
            print(f"  Verified d_min: {dmin.text if dmin is not None else 'N/A'} (expected 0.6)")
            print(f"  Verified d_max: {dmax.text if dmax is not None else 'N/A'} (expected 50.0)")
            print(f"  Verified scan width: {scan_width.text if scan_width is not None else 'N/A'} (expected 1.5)")
            print(f"  Verified Friedel: {friedel.text if friedel is not None else 'N/A'} (expected 0)")
            print(f"  Verified GRAL: {gral.text if gral is not None else 'N/A'} (expected 2)")
        
        autochem_section = root.find('__AUTOCHEM__SETTING__SECTION__')
        if autochem_section is not None:
            autochem_param = autochem_section.find('__default_AC_script__')
            print(f"  Verified AutoChem: {autochem_param.text if autochem_param is not None else 'N/A'} (expected 1)")

# Test 4: Handle missing file gracefully
print("\nTest 4: Handling missing XML file")
print("-" * 80)

try:
    proffit_missing = ProffitXML('nonexistent.xml', path=TEST_DATA_DIR, allow_missing=True, parse=False)
    print(f"✓ Created ProffitXML instance for missing file (allow_missing=True)")
    print(f"  File path: {proffit_missing.filename}")
except Exception as e:
    print(f"✗ Unexpected error with allow_missing=True: {e}")

try:
    proffit_error = ProffitXML('nonexistent.xml', path=TEST_DATA_DIR, allow_missing=False, parse=True)
    print(f"✗ Should have raised error for missing file with allow_missing=False")
except FileNotFoundError:
    print(f"✓ Correctly raised FileNotFoundError for missing file (allow_missing=False)")
except Exception as e:
    print(f"~ Raised exception (not FileNotFoundError): {type(e).__name__}: {e}")

# Test 5: Template-based creation
print("\nTest 5: Creating new XML from template")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    # Use existing XML as template
    new_proffit = ProffitXML('new_experiment.xml', path=tmpdir, allow_missing=True, parse=False)
    
    new_proffit.set_parameters(
        template=TEST_XML,  # Use test file as template
        laue=4,  # mmm
        d_min=0.7,
        d_max=100.0,
        scan_width=2.0,
        friedel_mates=True,
        gral_mode=1,  # Auto
        autochem=False
    )
    
    new_xml_path = os.path.join(tmpdir, 'new_experiment.xml')
    print(f"✓ Created new XML from template: {new_xml_path}")
    print(f"  File exists: {os.path.exists(new_xml_path)}")
    
    # Verify it can be loaded
    if os.path.exists(new_xml_path):
        verify_new = ProffitXML('new_experiment.xml', path=tmpdir, parse=True)
        if verify_new.tree is not None:
            root = verify_new.tree.getroot()
            params = root.find('__PROFFIT__PARAMETERS__')
            if params is not None:
                dmin = params.find('__dmin__')
                print(f"  Verified d_min in new file: {dmin.text if dmin is not None else 'N/A'}")

# Test 6: Update existing file
print("\nTest 6: Update existing XML with new parameters")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    test_copy = os.path.join(tmpdir, 'update_test.xml')
    shutil.copy(TEST_XML, test_copy)
    
    proffit_update = ProffitXML('update_test.xml', path=tmpdir, parse=True)
    
    # Update with allow_missing=False (should work because file exists)
    proffit_update.update(allow_missing=False)
    print(f"✓ Successfully updated existing XML")
    
    # Modify after update
    proffit_update.set_parameters(d_min=0.5, d_max=200.0)
    print(f"✓ Modified parameters after update")

print("\n" + "=" * 80)
print("All ProffitXML tests completed!")
print("=" * 80)
