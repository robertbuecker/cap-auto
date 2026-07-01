# CAP Automation - Python Tools for CrysAlisPro

A Python toolkit for working with Rigaku CrysAlisPro (CAP) data and automation:

1. **CAP Listen Mode Interface** - Control CAP programmatically via listen mode
2. **ROD Image Reader** - Read native `.rodhypix` detector image files without CAP

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

### Example Notebooks

Check out the `examples/` directory for Jupyter notebooks demonstrating:

- **Image Visualization**: Display detector images and diffraction frames
- **CAP Automation**: Run autoprocessing, refine lattice, execute AutoChem
- **Data Analysis**: Extract and analyze diffraction data

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
3. **Cython (experimental)**: Optional compiled TY6 backend for smaller deployments
4. **Pure Python (fallback)**: Always available, but significantly slower

Install optimization packages for best performance:
```bash
pip install numba              # JIT acceleration
pip install cython             # Optional compiled TY6 backend
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

- `numba` - Fast image decompression (recommended)
- `cython` - Optional compiled TY6 backend for smaller deployments
- `dxtbx` - Fastest image decompression (C++ acceleration)
- `matplotlib` - For image visualization in examples
- `numpy` - For array operations (auto-installed with numba/matplotlib)

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
