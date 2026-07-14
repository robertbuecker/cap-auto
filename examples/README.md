# CAP-Auto Example Notebooks

This directory now contains only CAP automation examples for `cap-auto`.

## Prerequisites

- **Python 3.8+**
- **CrysAlisPro**

## Notebook

### CAP Automation (`02_cap_automation.ipynb`)

**Purpose:** Control CrysAlisPro programmatically for automated workflows.

**Topics:**

- Starting and connecting to CAP
- Loading experiments
- Executing single commands
- Running data reduction
- Batch and macro execution
- Command history and diagnostics

## Example Data

The notebook uses `example_data/exp_11317.zip`.

## Quick Start

```bash
cd examples
jupyter notebook
```

Open `02_cap_automation.ipynb` and run cells sequentially.

## Troubleshooting

### "Data not found"

- Run from the repository root or `examples/`
- Ensure `example_data/exp_11317.zip` exists

### "CAP not responding"

- Verify CAP is installed in `C:\Xcalibur\CrysAlisPro171.*.*`
- Close other CAP instances
- Increase startup timeout if needed

### "Module not found"

```bash
pip install -e .
```

## Further Reading

- [Main README](../README.md)
- [CAP Control](../cap_auto/cap_control.py)
