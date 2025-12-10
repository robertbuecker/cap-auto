from cap_auto.cap_files import parse_cap_csv, write_cap_csv

ds, cells, centrings = parse_cap_csv('example_data\\trehalose_results.csv', use_raw_cell=True)
print("Parsed experiment data:")
for d, cell, centring in zip(ds, cells, centrings):
    print(f"Experiment: {d['Experiment name']}, Cell: {cell}, Centring: {centring}")
    
# apply some selection
selected_indices = [i for i, cell in enumerate(cells) if cell[1] < 10.0]
print("\nSelected experiments (b < 10.0):")
for i in selected_indices:
    d = ds[i]
    cell = cells[i]
    centring = centrings[i]
    print(f"Experiment: {d['Experiment name']}, Cell: {cell}, Centring: {centring}")
    
write_cap_csv('example_data\\selected_trehalose_results.csv', [ds[i] for i in selected_indices])

# TODO: add more comprehensive tests for edge cases, e.g., missing data, different centring types, etc.
# TODO: confirm that written CSV can be read back correctly and is identical to original data for selected experiments.