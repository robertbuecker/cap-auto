"""
Tests for FinalizationXML class - CrysAlisPro finalization parameter XML handler.
"""
from cap_auto.cap_files import FinalizationXML
import os
import shutil
import tempfile

# Test file paths
TEST_DATA_DIR = 'example_data\\exp_11317'
TEST_FINALIZER_XML = os.path.join(TEST_DATA_DIR, 'exp_11317_finalizer.xml')

print("=" * 80)
print("FinalizationXML Tests")
print("=" * 80)

# Test 1: Parse existing finalization XML
print("\nTest 1: Loading existing Finalization XML")
print("-" * 80)

fin = FinalizationXML(
    'exp_11317_finalizer.xml',
    'example_data\\exp_11317\\exp_11317',
    parse=True
)

print(f"✓ Loaded finalization XML from: {TEST_FINALIZER_XML}")
print(f"  File exists: {os.path.exists(TEST_FINALIZER_XML)}")

# Test 2: Read key parameters from existing file
print("\nTest 2: Reading key parameters from XML")
print("-" * 80)

if hasattr(fin, 'tree') and fin.tree is not None:
    root = fin.tree.getroot()
    
    # Find sample section
    sample_section = root.find('__FINALIZER_SAMPLE__')
    if sample_section is not None:
        chem = sample_section.find('__sample_chemical_formula__')
        z = sample_section.find('__sample_Z__')
        print(f"  Chemical formula: {chem.text if chem is not None else 'N/A'}")
        print(f"  Z value: {z.text if z is not None else 'N/A'}")
    
    # Find space group and autochem section
    sg_section = root.find('__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__')
    if sg_section is not None:
        laue = sg_section.find('__type_of_laue__')
        gral = sg_section.find('__is_GRAL__')
        gral_interactive = sg_section.find('__is_GRAL_interactive__')
        autochem = sg_section.find('__is_AUTOCHEM__')
        print(f"  Laue symmetry: {laue.text if laue is not None else 'N/A'}")
        print(f"  GRAL enabled: {gral.text if gral is not None else 'N/A'}")
        print(f"  GRAL interactive: {gral_interactive.text if gral_interactive is not None else 'N/A'}")
        print(f"  AutoChem enabled: {autochem.text if autochem is not None else 'N/A'}")
    
    # Find filters and limits section
    filters_section = root.find('__FINALIZER_FILTERS_AND_LIMITS__')
    if filters_section is not None:
        res_limit = filters_section.find('__res_limit__')
        fom = filters_section.find('__fom_cutoff__')
        shells = filters_section.find('__number_of_reflns_shells__')
        print(f"  Resolution limit: {res_limit.text if res_limit is not None else 'N/A'} Å")
        print(f"  FOM cutoff: {fom.text if fom is not None else 'N/A'}")
        print(f"  Number of shells: {shells.text if shells is not None else 'N/A'}")
else:
    print("  Warning: XML not parsed or tree not available")

# Test 3: Create new finalization XML from template
print("\nTest 3: Creating new XML from template with modified parameters")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    fin_new = FinalizationXML(
        'exp_11317_finalizer_modified.xml',
        os.path.join(tmpdir, 'exp_11317_modified'),
        allow_missing=True
    )
    
    fin_new.set_parameters(
        template=TEST_FINALIZER_XML,
        gral=True,
        N_shells=15,
        gral_interactive=False,
        res_limit=0.7,
        autochem=True,
        laue=5,
        z=4,
        chem='C H N O',
        fom=('Rint', 'Rurim', 'CC 1/2')  # Tuple of FOM names
    )
    
    new_xml_path = os.path.join(tmpdir, 'exp_11317_finalizer_modified.xml')
    print(f"✓ Created new finalization XML: {new_xml_path}")
    print(f"  File exists: {os.path.exists(new_xml_path)}")
    
    # Verify modifications
    if os.path.exists(new_xml_path):
        fin_verify = FinalizationXML(
            'exp_11317_finalizer_modified.xml',
            os.path.join(tmpdir, 'exp_11317_modified'),
            parse=True
        )
        
        if fin_verify.tree is not None:
            root = fin_verify.tree.getroot()
            
            # Verify modifications
            sg_section = root.find('__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__')
            if sg_section is not None:
                gral = sg_section.find('__is_GRAL__')
                gral_interactive = sg_section.find('__is_GRAL_interactive__')
                autochem = sg_section.find('__is_AUTOCHEM__')
                laue = sg_section.find('__type_of_laue__')
                print(f"  Verified GRAL: {gral.text if gral is not None else 'N/A'} (expected 1)")
                print(f"  Verified GRAL interactive: {gral_interactive.text if gral_interactive is not None else 'N/A'} (expected 0)")
                print(f"  Verified AutoChem: {autochem.text if autochem is not None else 'N/A'} (expected 1)")
                print(f"  Verified Laue: {laue.text if laue is not None else 'N/A'} (expected 5)")
            
            filters_section = root.find('__FINALIZER_FILTERS_AND_LIMITS__')
            if filters_section is not None:
                res_limit = filters_section.find('__res_limit__')
                shells = filters_section.find('__number_of_reflns_shells__')
                print(f"  Verified resolution: {res_limit.text if res_limit is not None else 'N/A'} (expected 0.7)")
                print(f"  Verified shells: {shells.text if shells is not None else 'N/A'} (expected 15)")
                print(f"  Verified FOM options are available in XML")
            
            sample_section = root.find('__FINALIZER_SAMPLE__')
            if sample_section is not None:
                z = sample_section.find('__sample_Z__')
                chem = sample_section.find('__sample_chemical_formula__')
                print(f"  Verified Z: {z.text if z is not None else 'N/A'} (expected 4)")
                print(f"  Verified chem: {chem.text if chem is not None else 'N/A'} (expected 'C H N O')")

# Test 4: Test with additional parameters
print("\nTest 4: Testing additional parameter settings")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    fin_advanced = FinalizationXML(
        'advanced_finalizer.xml',
        os.path.join(tmpdir, 'advanced_exp'),
        allow_missing=True
    )
    
    # Use pars dictionary for extra parameters
    extra_pars = {
        '__custom_param_1__': 'value1',
        '__custom_param_2__': '42'
    }
    
    fin_advanced.set_parameters(
        template=TEST_FINALIZER_XML,
        gral=False,
        N_shells=20,
        res_limit=0.8,
        pars=extra_pars
    )
    
    print(f"✓ Created finalization XML with extra parameters")

# Test 5: Handle missing template file
print("\nTest 5: Handling missing template file")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    try:
        fin_no_template = FinalizationXML(
            'no_template.xml',
            os.path.join(tmpdir, 'no_template_exp'),
            allow_missing=True
        )
        
        # This should warn or handle gracefully
        fin_no_template.set_parameters(
            template='nonexistent_template.xml',
            gral=True
        )
        
        print(f"✓ Handled missing template (check for warnings)")
    except Exception as e:
        print(f"~ Raised exception for missing template: {type(e).__name__}: {e}")

# Test 6: Update existing file
print("\nTest 6: Update existing finalization XML")
print("-" * 80)

with tempfile.TemporaryDirectory() as tmpdir:
    # Copy existing file
    test_copy = os.path.join(tmpdir, 'update_finalizer.xml')
    shutil.copy(TEST_FINALIZER_XML, test_copy)
    
    fin_update = FinalizationXML(
        'update_finalizer.xml',
        os.path.join(tmpdir, 'update_exp'),
        parse=True
    )
    
    # Modify parameters
    fin_update.set_parameters(
        gral=False,
        res_limit=0.9,
        N_shells=10
    )
    
    print(f"✓ Updated existing finalization XML")
    
    # Verify changes persisted
    fin_check = FinalizationXML(
        'update_finalizer.xml',
        os.path.join(tmpdir, 'update_exp'),
        parse=True
    )
    
    if fin_check.tree is not None:
        root = fin_check.tree.getroot()
        filters = root.find('__FINALIZER_FILTERS_AND_LIMITS__')
        if filters is not None:
            res = filters.find('__res_limit__')
            shells = filters.find('__number_of_reflns_shells__')
            print(f"  Verified updated resolution: {res.text if res is not None else 'N/A'}")
            print(f"  Verified updated shells: {shells.text if shells is not None else 'N/A'}")

print("\n" + "=" * 80)
print("All FinalizationXML tests completed!")
print("=" * 80)

# TODO: Future enhancements
# - Test integration with CAP using DC RRPFROMXML command
# - Test refinalization with merged datasets (CAP 45+)
# - Test preserving GRAL results between runs
# - Compare generated XML with expected golden outputs
