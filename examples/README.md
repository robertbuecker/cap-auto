# CAP-Auto Example Notebooks

This directory contains Jupyter notebooks demonstrating the `cap-auto` package for CrysAlisPro automation and data analysis.

## Prerequisites

- **Python 3.8+** with `numpy` installed
- **CrysAlisPro** (for CAP automation notebook only)
- **Optional:** `matplotlib` for visualization, `numba` for fast image reading

Install optional dependencies:
```bash
pip install matplotlib numba
```

## Notebooks

### 1. Image Visualization (`01_image_visualization.ipynb`)

**Purpose:** Read and visualize ROD detector images without launching CAP

**Topics:**
- Reading `.rodhypix` files with `RODImageReader`
- Displaying real-space images (grain snapshots)
- Visualizing diffraction frames
- Dynamic range adjustment using percentiles
- Accessing image metadata

**Run time:** ~1-2 minutes  
**Requires CAP:** No

---

### 2. CAP Automation (`02_cap_automation.ipynb`)

**Purpose:** Control CrysAlisPro programmatically for automated workflows

**Topics:**
- Starting and connecting to CAP
- Loading experiments
- Executing single commands
- Running data reduction (proffit, rrp)
- Batch command execution (macro mode)
- Command history and diagnostics

**Run time:** ~5-10 minutes (depends on data processing)  
**Requires CAP:** Yes

---

## Example Data

Both notebooks use the same example dataset (`exp_11317`) which is included as a ZIP file in `example_data/exp_11317.zip`.

The notebooks will automatically:
1. Check if data is already extracted
2. Extract from ZIP if needed
3. Use the data for demonstrations

**Dataset info:**
- Type: MicroED diffraction data
- Detector: HyPix (Rigaku)
- Contains: Grain snapshots, diffraction frames, processed data

## Quick Start

1. **Launch Jupyter:**
   ```bash
   cd examples
   jupyter notebook
   ```

2. **Start with image visualization** (no CAP needed):
   - Open `01_image_visualization.ipynb`
   - Run all cells (Shift+Enter)

3. **Try CAP automation** (requires CAP installed):
   - Open `02_cap_automation.ipynb`
   - Run cells sequentially
   - CAP will launch automatically

## Tips

### For Image Visualization

- **Real-space images:** Use 2-98 percentile range, linear scale
- **Diffraction frames:** Use 0.1-99.9 percentile range, log scale
- **Colormaps:** `gray` for real-space, `viridis` or `inferno` for diffraction

### For CAP Automation

- **First time:** Let CAP fully start (~10-20 seconds)
- **Errors:** Check `result.log_output` for detailed CAP messages
- **Timeouts:** Increase `timeout` parameter for slow commands
- **Cleanup:** Always call `cap.stop()` when finished

## Troubleshooting

### "Data not found"
- Ensure you're running from the `examples/` directory or repository root
- Check that `example_data/exp_11317.zip` exists

### "CAP not responding"
- Verify CAP is installed in `C:\Xcalibur\CrysAlisPro171.*.*`
- Close any other running CAP instances
- Increase startup timeout in notebook

### "Image decompression slow"
- Install `numba` for ~10x speedup: `pip install numba`
- Install `dxtbx` for ~50x speedup (requires cctbx)

### "Module not found"
- Install `cap-auto` in development mode:
  ```bash
  cd ..  # Go to repository root
  pip install -e .
  ```

## Further Reading

- [Main README](../README.md) - Package overview and API reference
- [ROD Image Reader](../cap_auto/rod_image_reader.py) - Image format documentation
- [CAP Control](../cap_auto/cap_control.py) - Automation API documentation

## License

BSD 3-Clause - see [LICENSE](../LICENSE)
