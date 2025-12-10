from cap_auto.cap_files import parse_cap_meta, get_diff_info
from cap_auto.cap_control import CAPInstance
import pprint

# use test data from example_data\exp_11317
info_single = parse_cap_meta('example_data\\exp_11317')

cap = CAPInstance(start_now=False, min_cap_version='45.50')
pprint.pprint(info_single)

# TODO this will not even work, as get_diff_info is (at minimum) broken because still using the old CAPInstance interface
shelldata, peak_table, powder, diff_img_fn = get_diff_info('example_data\\exp_11317\\exp_11317', cap=cap)

# TODO: updated tests, as a better version of working with diffraction info is coming