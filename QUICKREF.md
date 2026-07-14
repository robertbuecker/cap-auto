# Quick Reference Card

## Basic Usage

```python
from cap_auto.cap_control import CAPInstance

# Start CAP
cap = CAPInstance(start_now=True)

# Execute command
result = cap.execute("dc proffit")

# Check result
if result.success:
    print("✓ Success")
else:
    print(f"✗ Failed: {result.errors}")

# Stop CAP
cap.stop()
```

## Common Operations

### Execute Commands

```python
# Single command
result = cap.execute("dc proffit")

# Multiple commands (individual tracking)
results = cap.execute_batch(["cmd1", "cmd2", "cmd3"])

# Multiple commands (fast, as macro)
result = cap.execute_macro(["cmd1", "cmd2", "cmd3"])
```

### Work with Results

```python
result.command         # Command executed
result.success         # True/False
result.log_output      # Full log text
result.warnings        # List of warning messages
result.errors          # List of error messages  
result.execution_time  # Seconds
result.has_warnings()  # Check for warnings
result.has_errors()    # Check for errors
```

### Load Experiment

```python
cap.load_experiment("path/to/experiment.par")
```

### Multiple Experiments

```python
results = cap.execute_on_multiple_experiments(
    commands="dc proffit",
    par_files=["exp1.par", "exp2.par", "exp3.par"]
)
```

## Error Handling

### Benign (no exceptions)

```python
cap = CAPInstance(raise_on_error=False)
result = cap.execute("dc proffit")
if not result.success:
    print(f"Failed: {result.errors}")
```

### With exceptions

```python
try:
    result = cap.execute("dc proffit")
except CAPCommandError as e:
    print(f"Command: {e.command}")
    print(f"Log: {e.log_output}")
```

### Custom patterns

```python
cap = CAPInstance(
    error_patterns=[r'^\?.*', r'^ERROR:', r'custom error'],
    warning_patterns=[r'^WARNING:', r'custom warning']
)
```

## History

```python
# Access command history
for cmd in cap.history:
    print(f"{cmd.command}: {cmd.success}")

# Last command
last_result = cap.history[-1]
```

## Socket Server

```python
# Start server
port = cap.start_socket_server(port=9000)

# Stop server
cap.stop_socket_server()
```

## Context Manager

```python
with CAPInstance() as cap:
    result = cap.execute("dc proffit")
# Auto-cleanup
```

## Status

```python
cap.is_running()   # True/False
cap.get_status()   # 'idle', 'busy', or 'error'
```

## Common CAP Commands

### Data Collection
```python
cap.execute("dc simplescreen path base")
cap.execute("dc simplescan path base")
cap.execute("dc s runfile")
```

### Data Reduction  
```python
cap.execute("dc proffit")
cap.execute("dc rrp")
cap.execute("dc fullautoanalyse")
```

### Goniometer
```python
cap.execute("gt o 90")           # Omega
cap.execute("gt k 45")           # Kappa
cap.execute("gt p 180")          # Phi
cap.execute("gt d 50")           # Distance
cap.execute("gt a 0 0 0 0")      # All axes
```

### Video
```python
cap.execute("dc sfs")                # Start video
cap.execute("dc dosf image.jpg")    # Capture frame
cap.execute("dc efs")                # End video
```

## Tips

### Speed up multiple commands
```python
# Slow (4-5 seconds for 20 commands)
results = cap.execute_batch(commands)

# Fast (0.5-1 second for 20 commands)  
result = cap.execute_macro(commands)
```

### Check warnings
```python
result = cap.execute("dc proffit")
if result.has_warnings():
    for w in result.warnings:
        print(f"⚠ {w}")
```

### Timeout long operations
```python
result = cap.execute("dc proffit", timeout=300)  # 5 minutes
```

### Continue on errors
```python
results = cap.execute_batch(
    commands=["cmd1", "cmd2", "cmd3"],
    stop_on_error=False  # Process all even if one fails
)
```

