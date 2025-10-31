# Migration Guide: Old to Refactored API

This guide helps you migrate from the old `cap_control.py` to the refactored `cap_control_refactored.py`.

## Key Changes

### 1. Simplified Class Structure

**Old:**
```python
from cap_auto.cap_control import CAPInstance, CAPControl

cap_instance = CAPInstance(cap_folder="C:\\Xcalibur\\CrysAlisPro171.44.1", 
                          start_now=True)
cap_control = CAPControl(work_folder="C:\\Data", cap_instance=cap_instance)
cap_control.run("dc proffit")
```

**New:**
```python
from cap_auto.cap_control_refactored import CAPInstance

cap = CAPInstance(min_cap_version=44, max_cap_version=45, start_now=True)
cap.execute("dc proffit")
```

### 2. Command Execution

**Old:**
```python
# Single command
cap_instance.run_cmd("dc proffit", timeout=60)

# Multiple commands (always used macro)
cap_instance.run_cmd(["cmd1", "cmd2", "cmd3"], use_mac=True)

# Multiple experiments
cap_instance.run_cmd_multi_exp("dc proffit", ["exp1.par", "exp2.par"])
```

**New:**
```python
# Single command with result
result = cap.execute("dc proffit", timeout=60)
if result.success:
    print("Success!")

# Multiple commands as batch (individual tracking)
results = cap.execute_batch(["cmd1", "cmd2", "cmd3"])

# Multiple commands as macro (faster)
result = cap.execute_macro(["cmd1", "cmd2", "cmd3"])

# Multiple experiments
results = cap.execute_on_multiple_experiments(
    "dc proffit", 
    ["exp1.par", "exp2.par"]
)
```

### 3. Results and History

**Old:**
```python
# No structured results
cap_instance.last_command  # String only
# No history tracking
```

**New:**
```python
# Structured results
result = cap.execute("dc proffit")
print(result.command)        # Command executed
print(result.success)        # Boolean
print(result.log_output)     # Captured log
print(result.warnings)       # Parsed warnings
print(result.errors)         # Parsed errors
print(result.execution_time) # Seconds

# Complete history
for cmd_result in cap.history:
    print(f"{cmd_result.command}: {cmd_result.success}")
```

### 4. Error Handling

**Old:**
```python
try:
    cap_instance.run_cmd("dc proffit")
except CAPCommandError as e:
    print(str(e))  # Generic error message
```

**New:**
```python
try:
    result = cap.execute("dc proffit")
except CAPCommandError as e:
    print(e.command)            # The failed command
    print(e.log_output)         # Relevant log output
    print(e.error_file_content) # Content of command.error

# Or handle without exceptions
cap = CAPInstance(raise_on_error=False)
result = cap.execute("dc proffit")
if not result.success:
    print(f"Failed: {result.errors}")
```

### 5. Custom Error Patterns

**Old:**
```python
# Not available - hardcoded error detection
```

**New:**
```python
cap = CAPInstance(
    error_patterns=[
        r'^\?.*',           # CAP error indicator
        r'^ERROR:',         # Error prefix
        r'no peaks found'   # Custom pattern
    ],
    warning_patterns=[
        r'^WARNING:',
        r'low intensity'
    ]
)

result = cap.execute("dc proffit")
if result.has_warnings():
    print(f"Warnings found: {result.warnings}")
```

### 6. Log Handling

**Old:**
```python
# Log handle exists but not really used
cap_instance.update_log_handle()
# Manual log reading required
```

**New:**
```python
# Automatic log capture per command
result = cap.execute("dc proffit")
print(result.log_output)  # Full log output for this command

# Log position tracking handles rotation automatically
cap.load_experiment("new_exp.par")
result = cap.execute("dc proffit")  # Captures log from new file
```

### 7. Lifecycle Management

**Old:**
```python
cap = CAPInstance(start_now=True)
# ... use cap
cap.stop_cap(allow_stopped=True)

# Context manager marked as TODO
```

**New:**
```python
# Standard usage
cap = CAPInstance(start_now=True)
# ... use cap
cap.stop()

# Optional context manager
with CAPInstance() as cap:
    cap.execute("dc proffit")
# Automatic cleanup
```

### 8. Version Selection

**Old:**
```python
# Hardcoded version or full path
cap = CAPInstance(cap_folder="C:\\Xcalibur\\CrysAlisPro171.44.1")
```

**New:**
```python
# Version range selection (finds best match)
cap = CAPInstance(min_cap_version=44, max_cap_version=45)

# Or specific version
cap = CAPInstance(min_cap_version="44.1", max_cap_version="44.1")

# Or latest within range
cap = CAPInstance(min_cap_version=44)  # Uses latest >= 44
```

### 9. Status Checking

**Old:**
```python
status = cap_instance.status  # Returns string but uses property name
running = cap_instance.running
```

**New:**
```python
status = cap.get_status()   # Explicit method: 'idle', 'busy', 'error'
running = cap.is_running()  # Explicit method returns bool
```

### 10. Socket Server (New Feature)

**Old:**
```python
# Not available
```

**New:**
```python
# Start remote control server
port = cap.start_socket_server(port=9000)
print(f"Remote control on port {port}")

# From remote client:
import socket, json
sock = socket.socket()
sock.connect(('localhost', 9000))
sock.sendall(json.dumps({"command": "dc proffit"}).encode() + b'\n')
response = json.loads(sock.recv(4096))
print(f"Success: {response['success']}")
```

## Complete Migration Example

**Old code:**
```python
from cap_auto.cap_control import CAPInstance, CAPControl

# Setup
cap_instance = CAPInstance(
    cap_folder="C:\\Xcalibur\\CrysAlisPro171.44.1",
    cmd_folder="C:\\Xcalibur\\tmp\\listen_mode_offline",
    par_file="C:\\Data\\exp1\\exp1.par",
    start_now=True
)

cap_control = CAPControl("C:\\Data", cap_instance)

# Execute commands
try:
    cap_instance.run_cmd("dc proffit", timeout=300)
    cap_control.message("Data reduction completed")
    
    # Multiple commands
    cap_instance.run_cmd([
        "dc proffit",
        "dc rrp",
        "xx saveub"
    ], use_mac=True)
    
except CAPCommandError as e:
    cap_control.message(f"Error: {e}")

# Cleanup
cap_instance.stop_cap()
```

**New code:**
```python
from cap_auto.cap_control_refactored import CAPInstance

# Setup (simpler!)
cap = CAPInstance(
    min_cap_version=44,
    max_cap_version=45,
    cmd_folder="C:\\Xcalibur\\tmp\\listen_mode_offline",
    par_file="C:\\Data\\exp1\\exp1.par",
    start_now=True,
    message_callback=print  # Optional: custom handler
)

# Execute commands with results
try:
    result = cap.execute("dc proffit", timeout=300)
    if result.success:
        print("Data reduction completed")
        print(f"Time: {result.execution_time:.1f}s")
    
    # Multiple commands (faster with macro)
    result = cap.execute_macro([
        "dc proffit",
        "dc rrp",
        "xx saveub"
    ])
    
except CAPCommandError as e:
    print(f"Error in: {e.command}")
    print(f"Log excerpt: {e.log_output[:200]}")

# Cleanup
cap.stop()
```

## Backward Compatibility

The old `CAPControl` class is deprecated but still available:

```python
from cap_auto.cap_control_refactored import CAPInstance, CAPControl

# Old usage still works (with deprecation warning)
cap_instance = CAPInstance(start_now=True)
cap_control = CAPControl("C:\\Data", cap_instance)
cap_control.run("dc proffit")
```

However, **migrate to new API** for better functionality:

```python
cap = CAPInstance(start_now=True)
cap.execute("dc proffit")
```

## Testing Your Migration

Create a simple test to verify migration:

```python
def test_migration():
    """Test that migrated code works correctly"""
    cap = CAPInstance(min_cap_version=44, start_now=True)
    
    try:
        # Test single command
        result = cap.execute("xx sleep 1")
        assert result.success, "Command should succeed"
        assert result.execution_time > 0, "Should have execution time"
        
        # Test batch
        results = cap.execute_batch(["xx sleep 0.5", "xx sleep 0.5"])
        assert len(results) == 2, "Should have 2 results"
        assert all(r.success for r in results), "All should succeed"
        
        # Test macro
        result = cap.execute_macro(["xx sleep 0.5", "xx sleep 0.5"])
        assert result.success, "Macro should succeed"
        
        # Test history
        assert len(cap.history) >= 4, "Should have history of commands"
        
        print("✓ All migration tests passed!")
        
    finally:
        cap.stop()

if __name__ == '__main__':
    test_migration()
```

## Common Pitfalls

1. **Forgetting to check results**
   ```python
   # Old: No return value
   cap_instance.run_cmd("dc proffit")
   
   # New: Always returns result
   result = cap.execute("dc proffit")
   if not result.success:
       handle_error(result)
   ```

2. **Not handling macro failures**
   ```python
   # Macro execution is faster but error tracking is harder
   # Use batch if you need to know which command failed
   results = cap.execute_batch(commands)  # Slower, precise
   # vs
   result = cap.execute_macro(commands)   # Faster, less precise
   ```

3. **Ignoring log output**
   ```python
   # Log output is now captured automatically
   result = cap.execute("dc proffit")
   # Don't forget to use it!
   if result.has_warnings():
       print(f"Warnings: {result.warnings}")
   ```

## Need Help?

If you encounter issues during migration:

1. Check the examples in `examples.py`
2. Review the API reference in `README_REFACTORED.md`
3. The old API still works (with warnings) for gradual migration
4. Test incrementally - migrate one function at a time

## Benefits of Migration

- ✓ Structured results with log capture
- ✓ Command history tracking
- ✓ Custom error/warning patterns
- ✓ Better error messages with context
- ✓ Remote control via sockets
- ✓ Optional context manager support
- ✓ Cleaner, more maintainable code
- ✓ Better documentation and examples
