# CAP Automation for CrysAlisPro

`cap-auto` now contains only the CrysAlisPro automation tooling.

The native `.rodhypix` reader was split into a standalone package:

- Old import: `from cap_auto.rod_image_reader import ...`
- New import: `from rodhypix import ...`

## Scope

This package provides:

- `CAPInstance` for CAP listen mode control
- CAP command execution, batching, and macro helpers
- Log capture and error/warning parsing
- Native Windows directory monitoring via `pywin32`
- Optional socket server support for remote control

## Installation

```bash
pip install cap-auto
```

`cap-auto` is Windows-focused and expects a local CrysAlisPro installation.

## Quick Start

```python
from cap_auto.cap_control import CAPInstance

with CAPInstance() as cap:
    result = cap.execute("dc proffit")
    print(result.success)
    print(result.execution_time)
```

## Core Usage

### Execute one command

```python
cap = CAPInstance(start_now=True)
result = cap.execute("dc proffit")
cap.stop()
```

### Execute multiple commands

```python
cap = CAPInstance(start_now=True)

results = cap.execute_batch([
    "gt o 0",
    "gt k 90",
    "gt p 0",
])

macro_result = cap.execute_macro([
    "dc proffit",
    "dc rrp",
    "xx saveub",
])

cap.stop()
```

### Process several experiments

```python
cap = CAPInstance(start_now=True)

results = cap.execute_on_multiple_experiments(
    commands=["dc proffit", "dc rrp"],
    par_files=["exp1.par", "exp2.par", "exp3.par"],
    use_macro=True,
)

cap.stop()
```

## Examples

The root `examples/` directory now contains only CAP automation material.

- `examples/02_cap_automation.ipynb`
- `examples.py`
- `cap_server_gui.py`
- `cap_client_gui.py`

The reader notebook and benchmark moved into the standalone `rodhypix` tree in this workspace.

## Project Layout

- `cap_auto/cap_control.py`: CAP automation API
- `examples/02_cap_automation.ipynb`: CAP notebook
- `QUICKREF.md`: compact API cheatsheet

## Related Package

The extracted reader package lives under [rodhypix](./rodhypix) in this workspace and is intended to become its own repository and distribution.
