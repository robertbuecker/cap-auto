from cap_auto.cap_files import FinalizationXML

# first: does the parsing itself work?
fin = FinalizationXML('example_data\\exp_11317\\exp_11317_finalizer.xml', 
                      'example_data\\exp_11317\\exp_11317',
                      parse=True)

# generate new one
fin = FinalizationXML('example_data\\exp_11317\\exp_11317_finalizer_modified.xml',
                      'example_data\\exp_11317\\exp_11317_modified',
                      allow_missing=True)

fin.set_parameters(template='example_data\\exp_11317\\exp_11317_finalizer.xml',
                   gral=True,
                   N_shells=15,
                   gral_interactive=False,
                   res_limit=0.7)

# TODO: write tests to compare generated XML with expected output
# TODO: write tests to actually run finalization using DC RRPFROMXML with the generated XML and check results
# TODO: investigate XML files for other useful parameters/settings. Specifically, refinialization with merged data sets in CAP 45, and keeping GRAL result.