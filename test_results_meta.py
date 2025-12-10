from cap_auto.cap_files import parse_cap_meta
import pprint

# use test data from example_data\exp_11317
info_single = parse_cap_meta('example_data\\exp_11317')
pprint.pprint(info_single)

# use test data from example_data\trehalose_results.csv
# note: this will work only if they can be found in the correct absolute path
info_multiple = parse_cap_meta('example_data\\trehalose_results.csv')
pprint.pprint(info_multiple)

# still scans
info_still = parse_cap_meta('C:\\XcaliburData\\first_still_run\\grid 2')
pprint.pprint(info_still)

#TODO: add more comprehensive tests for edge cases, e.g., missing files, different formats, etc.
#TODO: confirm that metadata matches expected values for given test data
#TODO: test explicitly for queued collections vs single experiments
#TODO: test explicitly for still scans vs rotation scans