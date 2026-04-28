# CAP Automation - Python Tools for CrysAlisPro

A Python toolkit for working with Rigaku CrysAlisPro (CAP) data and automation:

1. **CAP Listen Mode Interface** - Control CAP programmatically via listen mode
2. **ROD Image Reader** - Read native `.rodhypix` detector image files without CAP
3. **File Parsing Utilities** - Parse CrysAlisPro output files (.tab, .dat, .xml, .csv) without CAP

Designed for scientists familiar with CAP who want to automate workflows and analyze data with Python.

## Features

### CAP Listen Mode Control (`CAPInstance`)

- **Simple API**: Clean, intuitive interface for CAP automation
- **Event-Driven Monitoring**: Native Windows file monitoring (zero polling overhead)
- **Robust Logging**: Automatic capture and parsing of CAP log output
- **Error Handling**: Customizable error/warning pattern matching
- **Three Execution Modes**:
  - `execute()`: Single command with full log capture
  - `execute_batch()`: Multiple commands with individual tracking  
  - `execute_macro()`: Fast macro execution for many commands
- **Remote Control**: Optional TCP socket server for external control
- **Command History**: Complete history of executed commands and their results
- **Context Manager Support**: Optional `with` statement usage for automatic cleanup

### ROD Image Reader (`RODImageReader`)

- **Native Format Support**: Read `.rodhypix` files directly (no CAP needed)
- **Fast Decompression**: C++ acceleration (via dxtbx) or Numba JIT compilation
- **Complete Metadata**: Access all image headers and experimental parameters
- **NumPy Integration**: Returns images as standard NumPy arrays
- **Pure Python Fallback**: Works even without C++ extensions

### File Parsing Utilities (`cap_files`)

- **CAP-Independent Parsing**: Read CrysAlisPro files without running CAP
- **Reflection Tables**: Parse `.tab` files (from `WD OLDASCIIT` command)
- **Powder Patterns**: Parse `.dat` files (from `POWDER RADIAL` command)
- **Shell Statistics**: Automatic resolution shell analysis with auto-suggested boundaries
- **XML Parameter Files**: Read and modify Proffit and Finalization XML settings
- **Experiment Metadata**: Extract comprehensive metadata from experiments and CSV results
- **Command Hints**: Parsing functions return CAP commands needed to generate missing files
- **Pure Python**: Uses only standard library + NumPy (no pandas dependency)

## Installation

```bash
# Clone the repository
git clone https://github.com/robertbuecker/cap-auto.git
cd cap-auto

# No required dependencies for basic usage!
# Optional: Install acceleration packages
pip install numba  # For fast image decompression
```

## Quick Start

### Reading Detector Images

```python
from cap_auto.rod_image_reader import read_rod_image, get_rod_info
import matplotlib.pyplot as plt

# Read image data
image = read_rod_image("snapshot.rodhypix")
print(f"Image shape: {image.shape}")
print(f"Data range: {image.min()} to {image.max()}")

# Display with percentile scaling
vmin, vmax = np.percentile(image, [1, 99])
plt.imshow(image, vmin=vmin, vmax=vmax, cmap='gray')
plt.colorbar()
plt.show()

# Get metadata
info = get_rod_info("snapshot.rodhypix")
print(f"Exposure time: {info['exposure_time_sec']:.3f} s")
print(f"Pixel size: {info['real_px_size_x']:.4f} mm")
```

### Controlling CAP

```python
from cap_auto.cap_control import CAPInstance

# Create and start CAP instance
cap = CAPInstance(start_now=True)

# Execute a command
result = cap.execute("dc proffit")

if result.success:
    print("Data reduction completed!")
    print(f"Execution time: {result.execution_time:.1f}s")
    
    if result.has_warnings():
        print(f"Warnings: {result.warnings}")
else:
    print("Command failed")
    print(result.log_output)

# Clean shutdown
cap.stop()
```

### Parsing CrysAlisPro Files

```python
from cap_auto.cap_files import parse_reflection_table, DiffractionData

# Parse reflection table (no CAP needed)
reflections, commands = parse_reflection_table("exp_11317.tab", wavelength=0.0251)
print(f"Parsed {len(reflections)} reflections")

# Analyze with automatic shell statistics
diff_data = DiffractionData(reflections, [], wavelength=0.0251)
shells = diff_data.compute_shell_statistics()  # Auto-suggested boundaries

for shell in shells:
    print(f"d: {shell['d_max']:.1f}-{shell['d_min']:.1f} Å, "
          f"N_peaks: {shell['N_peaks']}, ratio: {shell['peak_ratio']:.3f}")
```

### Example Notebooks

Check out the `examples/` directory for Jupyter notebooks demonstrating:

- **Image Visualization**: Display detector images and diffraction frames
- **CAP Automation**: Run autoprocessing, refine lattice, execute AutoChem
- **Data Analysis**: Extract and analyze diffraction data
- **File Parsing**: Parse reflection tables, powder patterns, and compute shell statistics
- **XML Modification**: Programmatically modify Proffit and Finalization parameters

## ROD Image Reader

### Basic Usage

```python
from cap_auto.rod_image_reader import RODImageReader
import numpy as np

# Create reader
reader = RODImageReader("image.rodhypix")

# Get image data
image = reader.get_raw_data()

# Access metadata
print(f"Image shape: {reader.get_image_shape()}")
print(f"Pixel size: {reader.get_pixel_size()} mm")
print(f"Exposure: {reader.get_exposure_time()} s")

# Check which decompression method is being used
print(f"Using: {reader.get_decompression_method()}")  # C++, Numba, or Python
```

### Performance Notes

The reader automatically selects the fastest available decompression:

1. **C++ (fastest)**: If `dxtbx` is installed, but large extra dependency
2. **Numba (fast)**: If `numba` is installed, almost as fast
3. **Pure Python (fallback)**: Always available, but significantly slower

Install optimization packages for best performance:
```bash
pip install numba              # JIT acceleration
pip install dxtbx              # C++ acceleration (requires cctbx)
```

### Metadata Access

```python
# Get complete header information
info = reader.get_header_info()

# Access specific fields
print(f"Wavelength: {info['alpha1_wavelength']} Å")
print(f"Distance: {info['distance_mm']} mm")
print(f"Detector type: {info['detector_type']}")
print(f"Goniometer angles: {info['start_angles_steps']}")
print(f"Gain: {info['gain']}")
```

## File Parsing Utilities

Parse CrysAlisPro output files independently from CAP. All parsing functions work without a running CAP instance and return empty results with warnings for missing files.

### Parse Reflection Tables

```python
from cap_auto.cap_files import parse_reflection_table

# Parse reflection table (from WD OLDASCIIT command)
reflections, commands = parse_reflection_table("exp_11317.tab", wavelength=0.0251)

print(f"Parsed {len(reflections)} reflections")

# Each reflection is a dict with fields:
for refl in reflections[:3]:
    print(f"d = {refl['d']:.2f} Å, I = {refl['I']:.1f}, inv_d = {refl['inv_d']:.3f}")

# If file is missing, get CAP commands to generate it:
if not reflections and commands:
    print(f"File missing! Run these CAP commands:")
    for cmd in commands:
        print(f"  {cmd}")
```

### Parse Powder Patterns

```python
from cap_auto.cap_files import parse_powder_pattern

# Parse powder pattern (from POWDER RADIAL command)
powder, commands = parse_powder_pattern("radial.dat")

print(f"Parsed {len(powder)} powder data points")

# Each point is a dict with fields: two_theta, d_value, intensity, sigma, count, inv_d
for point in powder[:3]:
    print(f"2θ = {point['two_theta']:.2f}°, d = {point['d_value']:.2f} Å, "
          f"I = {point['intensity']:.1f}")

# Total integrated intensity
total_intensity = sum(p['intensity'] for p in powder)
print(f"Total intensity: {total_intensity:.1f}")
```

### Diffraction Data Analysis with Shell Statistics

```python
from cap_auto.cap_files import DiffractionData, parse_reflection_table, parse_powder_pattern

# Load data
reflections, _ = parse_reflection_table("exp.tab", wavelength=0.0251)
powder, _ = parse_powder_pattern("radial.dat")

# Create DiffractionData object
diff_data = DiffractionData(reflections, powder, wavelength=0.0251)

# Compute shell statistics with auto-suggested boundaries
shells = diff_data.compute_shell_statistics()

# Display results
print(f"{'d_max':>8} {'d_min':>8} {'N_peaks':>8} {'I_peak':>12} {'I_tot':>12} {'ratio':>8}")
print("-" * 70)
for shell in shells:
    d_max = shell['d_max'] if shell['d_max'] != float('inf') else 999.9
    print(f"{d_max:8.2f} {shell['d_min']:8.2f} {shell['N_peaks']:8d} "
          f"{shell['I_peak']:12.1f} {shell['I_tot']:12.1f} {shell['peak_ratio']:8.3f}")

# Or specify custom shell boundaries (in 1/d, Å⁻¹)
custom_boundaries = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
shells_custom = diff_data.compute_shell_statistics(shell_boundaries=custom_boundaries)
```

### High-Level Diffraction Analysis

```python
from cap_auto.cap_files import get_diff_info

# Parse without CAP (reads existing files)
shells, reflections, powder, img_path = get_diff_info(
    "exp_11317",
    cap=None,  # No CAP instance needed
    wavelength=0.0251,
    keep_peak_file=True,
    keep_powder_file=True
)

print(f"Analyzed {len(reflections)} reflections in {len(shells)} shells")
print(f"Diffraction image: {img_path}")

# Or generate files using CAP and then parse
from cap_auto.cap_control import CAPInstance

cap = CAPInstance(start_now=True)
shells, reflections, powder, img_path = get_diff_info(
    "exp_11317",
    cap=cap,
    redo_peak_hunt=True,  # Re-run peak hunting
    wavelength=0.0251
)
cap.stop()
```

### Parse Experiment Metadata

```python
from cap_auto.cap_files import parse_cap_meta

# Parse single experiment directory
metadata = parse_cap_meta("exp_11317")
exp = metadata[0]

print(f"Name: {exp['name']}")
print(f"R_int: {exp['r_int']}")
print(f"Digest: {exp['digest']}")
print(f"Diffraction image: {exp.get('diff-jpg', 'N/A')}")

# Parse from Results Viewer CSV
metadata_csv = parse_cap_meta("results.csv")
print(f"Parsed {len(metadata_csv)} experiments from CSV")

# Filter results
good_data = [m for m in metadata_csv if m.get('r_int', 1.0) < 0.15]
print(f"Found {len(good_data)} experiments with R_int < 15%")
```

### Modify XML Parameter Files

```python
from cap_auto.cap_files import ProffitXML, FinalizationXML

# Proffit (data reduction) parameters
proffit = ProffitXML("exp.xml", path="exp_dir", allow_missing=True)
proffit.set_parameters(
    template="template.xml",  # Use existing file as template
    laue=5,                   # Laue group (4/m for tetragonal)
    d_min=0.8,                # Resolution limits
    d_max=50.0,
    scan_width=1.5,           # Scan width in degrees
    friedel_mates=True,       # Use Friedel mates
    gral_mode=1,              # GRAL: 0=OFF, 1=AUTO, 2=MANUAL
    autochem=False
)
# File is automatically saved

# Finalization parameters
finalizer = FinalizationXML("exp_finalizer.xml", path="exp_dir", allow_missing=True)
finalizer.set_parameters(
    template="template_finalizer.xml",
    gral=True,
    gral_interactive=False,
    N_shells=15,
    res_limit=0.7,
    autochem=True,
    laue=5,
    z=4,
    chem="C H N O"
)
```

### Generate CAP Commands for Missing Files

```python
from cap_auto.cap_files import (
    generate_powder_commands,
    generate_reflection_commands,
    generate_diff_image_commands
)

# Get commands to generate powder pattern
powder_cmds = generate_powder_commands(
    "exp_11317",
    wavelength=0.0251,
    d_min=0.3,
    d_max=20.0,
    recenter=True
)

# Get commands to generate reflection table
refl_cmds = generate_reflection_commands(
    "exp_11317",
    redo_peak_hunt=True
)

# Get commands to generate diffraction image
img_cmds = generate_diff_image_commands("exp_11317")

# Execute with CAP
from cap_auto.cap_control import CAPInstance
cap = CAPInstance(start_now=True)

for cmd in powder_cmds + refl_cmds + img_cmds:
    result = cap.execute(cmd)
    print(f"{'✓' if result.success else '✗'} {cmd}")

cap.stop()
```

## CAP Listen Mode Control

### Basic Command Execution

```python
# Automatic start/stop with context manager
with CAPInstance() as cap:
    result = cap.execute("dc proffit")
    print(f"Success: {result.success}")
# CAP automatically stopped here
```

### Event-Driven Monitoring

The listen mode interface uses **native Windows file monitoring** (via `pywin32`'s `ReadDirectoryChangesW`) for instant response with zero CPU overhead.

### Multiple Commands

```python
cap = CAPInstance(start_now=True)

# Method 1: Batch (slower, individual tracking)
results = cap.execute_batch([
    "gt o 0",
    "gt k 90",
    "gt p 0"
])

# Method 2: Macro (faster, ~5-10x speedup)
result = cap.execute_macro([
    "dc proffit",
    "dc rrp",
    "xx saveub"
])

cap.stop()
```

### Process Multiple Experiments

```python
cap = CAPInstance(start_now=True)

results = cap.execute_on_multiple_experiments(
    commands=["dc proffit", "dc rrp"],
    par_files=["exp1.par", "exp2.par", "exp3.par"],
    use_macro=True
)

for result in results:
    print(f"{'✓' if result.success else '✗'} {result.command}")

cap.stop()
```

## Advanced Usage

### Custom Error Patterns

```python
cap = CAPInstance(
    start_now=True,
    error_patterns=[
        r'^\?.*',           # Lines starting with ?
        r'^ERROR:',         # Lines starting with ERROR:
        r'no peaks found'   # Custom pattern
    ],
    warning_patterns=[
        r'^WARNING:',
        r'low intensity'
    ],
    raise_on_error=False,    # Return results instead of raising
    raise_on_warning=False
)

result = cap.execute("dc proffit")

# Check for specific issues
if result.errors:
    print(f"Errors detected: {result.errors}")

if result.warnings:
    print(f"Warnings: {result.warnings}")
```

### Access Command History

```python
cap = CAPInstance(start_now=True)

# Run several commands
cap.execute("dc proffit")
cap.execute("dc rrp")
cap.execute("xx saveub")

# Review history
print(f"Executed {len(cap.history)} commands:")
for cmd_result in cap.history:
    status = '✓' if cmd_result.success else '✗'
    print(f"{status} {cmd_result.command} ({cmd_result.execution_time:.2f}s)")
```

### Remote Control via Socket

```python
# Start socket server
cap = CAPInstance(start_now=True)
port = cap.start_socket_server(port=9000)
print(f"Remote control on port {port}")

# From another Python script or program:
import socket, json

sock = socket.socket()
sock.connect(('localhost', 9000))

# Send command
command = {"command": "dc proffit", "timeout": 60}
sock.sendall(json.dumps(command).encode() + b'\n')

# Receive result
response = json.loads(sock.recv(4096))
print(f"Success: {response['success']}")
print(f"Log output: {response['log_output']}")

sock.close()
```

### GUI Integration with Callbacks

```python
def update_status_bar(msg):
    """Your GUI status bar update function"""
    status_label.set_text(msg)

def show_input_dialog(prompt):
    """Your GUI input dialog"""
    dialog.show(prompt)

def get_user_input():
    """Get response from GUI"""
    return dialog.get_response()

cap = CAPInstance(
    start_now=True,
    message_callback=update_status_bar,
    request_callback=show_input_dialog,
    response_callback=get_user_input
)
```

## API Reference

### CAPInstance

Main class for controlling CAP.

#### Constructor Parameters

- `max_cap_version` (int, tuple, or str): Maximum CAP version (default: 100)
- `min_cap_version` (int, tuple, or str): Minimum CAP version (default: 44)
- `cmd_folder` (str): Folder for listen mode files (default: `C:\Xcalibur\tmp\listen_mode_offline`)
- `par_file` (str, optional): Initial experiment .par file
- `start_now` (bool): Start CAP immediately (default: False)
- `error_patterns` (List[str], optional): Regex patterns for errors
- `warning_patterns` (List[str], optional): Regex patterns for warnings  
- `raise_on_error` (bool): Raise exception on command failure (default: True)
- `raise_on_warning` (bool): Raise exception on warnings (default: False)
- `message_callback`, `request_callback`, `response_callback`: Optional GUI integration

#### Methods

##### Core Methods

- `start(timeout=20)`: Start CAP process
- `stop(allow_stopped=False)`: Stop CAP process
- `is_running()`: Check if CAP is running
- `get_status()`: Get listen mode status ('idle', 'busy', or 'error')

##### Experiment Management

- `load_experiment(par_file)`: Load different experiment

##### Command Execution

- `execute(cmd, timeout=None, raise_on_error=None)`: Execute single command
  - Returns `CAPCommandResult`
  
- `execute_batch(commands, timeout=None, stop_on_error=True)`: Execute multiple commands individually
  - Returns `List[CAPCommandResult]`
  
- `execute_macro(commands, timeout=None)`: Execute multiple commands as macro (faster)
  - Returns `CAPCommandResult`
  
- `execute_on_multiple_experiments(commands, par_files, use_macro=True)`: Run commands on multiple experiments
  - Returns `List[CAPCommandResult]`

##### Communication

- `message(msg)`: Send message via callback
- `request(prompt)`: Send request and get response

##### Remote Control

- `start_socket_server(port=0, host='localhost')`: Start TCP server
- `stop_socket_server()`: Stop TCP server

#### Properties

- `history`: List of all `CAPCommandResult` objects
- `cap_version`: Tuple of (major, minor) version
- `log_file`: Current log file path

### CAPCommandResult

Result object returned by command execution.

#### Attributes

- `command` (str): The executed command
- `success` (bool): Whether command succeeded
- `log_output` (str): Captured log output
- `warnings` (List[str]): Warning messages found
- `errors` (List[str]): Error messages found
- `execution_time` (float): Execution time in seconds

#### Methods

- `has_warnings()`: Check if warnings present
- `has_errors()`: Check if errors present

### Exceptions

- `CAPListenModeError`: Listen mode communication failure
- `CAPCommandError`: Command execution failure (includes command, log_output, error_file_content)
- `CAPRuntimeError`: CAP runtime issue

## Design Philosophy

This wrapper is intentionally **thin and simple**:

1. **Minimal abstractions**: Direct mapping to CAP commands
2. **Scientist-friendly**: Designed for CAP experts, not Python experts
3. **Explicit over implicit**: Clear, predictable behavior
4. **Robust error handling**: Benign failure modes with detailed context
5. **No hidden magic**: What you see is what you get

## Listen Mode Overview

The listen mode interface uses simple text files in a command folder:

- `command.in`: Your command goes here
- `command.busy`: CAP is executing
- `command.done`: Command completed successfully
- `command.error`: Command failed
- `command.stop`: Request to stop execution
- `command.mac`: Macro file for batch commands

This wrapper handles all the file management automatically.

## Tips for CAP Users

### When to Use Each Execution Mode

**execute()** - Single commands, need detailed log output:
```python
result = cap.execute("dc proffit")
```

**execute_batch()** - Multiple commands, need to track each one:
```python
results = cap.execute_batch(["cmd1", "cmd2", "cmd3"])
# Slower, but you know which command failed
```

**execute_macro()** - Many commands, speed is important:
```python
result = cap.execute_macro(["cmd1", "cmd2", ..., "cmd20"])
# ~5-10x faster, but harder to pinpoint failures
```

### Error Pattern Examples

Common CAP error indicators:
```python
error_patterns = [
    r'^\?.*',                    # Lines starting with ?
    r'^ERROR:',                  # ERROR: prefix
    r'^FATAL:',                  # FATAL: prefix
    r'no peaks found',           # Specific failure
    r'cannot (open|read|write)', # File access issues
    r'out of range',             # Parameter issues
]
```

### Supported Commands

All CAP listen mode commands are supported. See `EReferenceSection_Issues_ITS_144.html` for full documentation.

Common commands:
- Data collection: `dc s`, `dc simplescreen`, `dc simplescan`
- Data reduction: `dc proffit`, `dc rrp`, `dc fullautoanalyse`
- Goniometer: `gt a`, `gt o`, `gt k`, `gt p`, `gt d`
- Experiments: `xx selectexpnogui`, `xx saveub`, `xx recallub`
- System: `xx sleep`, `xx listenmode`
- Video: `dc sfs`, `dc dosf`, `dc efs`


## Troubleshooting

### CAP doesn't start
- Check CAP is installed in `C:\Xcalibur\CrysAlisPro171.*.*`
- Verify version range with `min_cap_version` and `max_cap_version`
- Check no other CAP instance is using the same `cmd_folder`

### Commands timeout
- Increase timeout: `cap.execute("dc proffit", timeout=300)`
- Check CAP window isn't showing a dialog waiting for input
- Verify command syntax is correct

### Log output missing
- Log files are in experiment folder: `{experiment_path}/log/`
- Check experiment is loaded: `cap.load_experiment("path/to/exp.par")`
- Log capture happens after command completes

### Socket server connection refused
- Check firewall settings
- Verify port isn't already in use
- Use `port=0` for automatic port selection

### Image reader performance
- Install `numba` for ~10x speedup: `pip install numba`
- Install `dxtbx` for ~20-50x speedup (requires cctbx installation)

## Requirements

- **Python 3.8+**
- **Windows** (for CAP control; image reader works on any platform)
- **pywin32** (usually pre-installed on Windows Python)
- **CrysAlisPro** (for CAP control; not needed for image reading)

### Optional Dependencies

- `numpy` - Required for file parsing utilities; recommended for all data analysis
- `numba` - Fast image decompression (recommended)
- `dxtbx` - Fastest image decompression (C++ acceleration)
- `matplotlib` - For image visualization in examples

## Contributing

This toolkit is intentionally kept simple and focused. When contributing:

- Keep it simple - avoid complex abstractions
- Document for CAP users, not Python experts
- Maintain backward compatibility
- Add tests for new features

## License

BSD 3-Clause License. See LICENSE file for details.

## Author

Robert Bücker, robert.buecker@rigaku.com

## Acknowledgments

- Listen mode interface based on Rigaku CrysAlisPro documentation (ITS 144)
- ROD image reader adapted from [dxtbx](https://github.com/cctbx/dxtbx) (BSD 3-Clause)
  - Original authors: David Waterman, Takanori Nakane
  - Copyright: 2018-2023 United Kingdom Research and Innovation & 2022-2023 Takanori Nakane
