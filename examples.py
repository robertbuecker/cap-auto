"""
Example usage of the refactored CAP automation interface.

This demonstrates the simplified API for scientists familiar with CAP
but potentially new to Python automation.
"""

from cap_auto.cap_control import CAPInstance, CAPCommandError

def example_basic_usage():
    """Example 1: Basic command execution"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Create CAP instance (starts automatically)
    cap = CAPInstance(start_now=True)
    
    try:
        # Execute a single command
        result = cap.execute("dc proffit")
        
        if result.success:
            print("✓ Data reduction completed successfully")
            print(f"  Execution time: {result.execution_time:.1f}s")
            
            if result.has_warnings():
                print(f"  ⚠ Warnings found: {len(result.warnings)}")
                for w in result.warnings[:3]:  # Show first 3
                    print(f"    - {w}")
        else:
            print("✗ Data reduction failed")
            print(f"  Log excerpt:\n{result.log_output[:500]}")
        
    finally:
        cap.stop()


def example_context_manager():
    """Example 2: Using context manager (optional)"""
    print("\n" + "=" * 60)
    print("Example 2: Context Manager")
    print("=" * 60)
    
    # Context manager automatically starts/stops CAP
    with CAPInstance() as cap:
        result = cap.execute("xx sleep 2")
        print(f"Command executed: {result.command}")
        print(f"Success: {result.success}")
    
    print("CAP automatically stopped when context exited")


def example_batch_vs_macro():
    """Example 3: Batch vs Macro execution"""
    print("\n" + "=" * 60)
    print("Example 3: Batch vs Macro")
    print("=" * 60)
    
    cap = CAPInstance(start_now=True)
    
    commands = [
        "gt o 0",
        "gt k 90",
        "gt p 0",
        "ty a"
    ]
    
    try:
        # Method 1: Batch (slower, but individual command tracking)
        print("\nMethod 1: Batch execution (individual commands)")
        import time
        t0 = time.time()
        results = cap.execute_batch(commands)
        batch_time = time.time() - t0
        print(f"  Batch completed in {batch_time:.2f}s")
        print(f"  Commands: {len(results)}, All successful: {all(r.success for r in results)}")
        
        # Method 2: Macro (faster, but less granular error tracking)
        print("\nMethod 2: Macro execution (all at once)")
        t0 = time.time()
        result = cap.execute_macro(commands)
        macro_time = time.time() - t0
        print(f"  Macro completed in {macro_time:.2f}s")
        print(f"  Success: {result.success}")
        print(f"  Speedup: {batch_time/macro_time:.1f}x faster")
        
    finally:
        cap.stop()


def example_multiple_experiments():
    """Example 4: Processing multiple experiments"""
    print("\n" + "=" * 60)
    print("Example 4: Multiple Experiments")
    print("=" * 60)
    
    cap = CAPInstance(start_now=True)
    
    par_files = [
        "C:\\Data\\experiment1\\experiment1.par",
        "C:\\Data\\experiment2\\experiment2.par",
        "C:\\Data\\experiment3\\experiment3.par",
    ]
    
    try:
        # Execute same commands on all experiments
        results = cap.execute_on_multiple_experiments(
            commands=["dc proffit", "dc rrp", "xx saveub"],
            par_files=par_files,
            use_macro=True
        )
        
        print(f"\nProcessed {len(results)} experiments:")
        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            exp_name = os.path.basename(par_files[i-1])
            print(f"  {status} {exp_name}: {result.execution_time:.1f}s")
        
    finally:
        cap.stop()


def example_error_handling():
    """Example 5: Error handling and pattern matching"""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)
    
    # Customize error/warning patterns
    cap = CAPInstance(
        start_now=True,
        error_patterns=[
            r'^\?.*',           # Lines starting with ?
            r'^ERROR:',         # Lines starting with ERROR:
            r'^FATAL:',         # Lines starting with FATAL:
            r'no peaks found'   # Custom pattern
        ],
        warning_patterns=[
            r'^WARNING:',
            r'low intensity'
        ],
        raise_on_error=False  # Don't raise exceptions, return results
    )
    
    try:
        # This command might fail
        result = cap.execute("dc proffit")
        
        if not result.success:
            print("Command failed, but no exception raised")
            print(f"Errors found: {result.errors}")
        
        # Check command history
        print(f"\nCommand history: {len(cap.history)} commands executed")
        for cmd_result in cap.history[-5:]:  # Last 5
            status = "✓" if cmd_result.success else "✗"
            print(f"  {status} {cmd_result.command} ({cmd_result.execution_time:.2f}s)")
        
    finally:
        cap.stop()


def example_remote_control():
    """Example 6: Remote control via socket"""
    print("\n" + "=" * 60)
    print("Example 6: Remote Control Socket Server")
    print("=" * 60)
    
    cap = CAPInstance(start_now=True)
    
    try:
        # Start socket server for remote control
        port = cap.start_socket_server(port=9000)
        print(f"Socket server listening on port {port}")
        print("\nYou can now control CAP remotely by sending JSON commands:")
        print('  {"command": "dc proffit", "timeout": 60}')
        print("\nExample using Python client:")
        print("""
import socket, json

sock = socket.socket()
sock.connect(('localhost', 9000))
sock.sendall(json.dumps({"command": "dc proffit"}).encode() + b'\\n')
response = sock.recv(4096)
result = json.loads(response)
print(f"Success: {result['success']}")
sock.close()
        """)
        
        # Keep running for a while to accept connections
        input("\nPress Enter to stop socket server...")
        
        cap.stop_socket_server()
        
    finally:
        cap.stop()


def example_custom_callbacks():
    """Example 7: Custom message/request callbacks"""
    print("\n" + "=" * 60)
    print("Example 7: Custom Callbacks for GUI Integration")
    print("=" * 60)
    
    # Example: logging to file instead of stdout
    log_file = open('cap_automation.log', 'w')
    
    def log_message(msg):
        """Custom message handler"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f'[{timestamp}] {msg}\n')
        log_file.flush()
        print(f'LOG: {msg}')
    
    def request_input(prompt):
        """Custom request handler"""
        print(f'REQUEST: {prompt}')
    
    def get_response():
        """Custom response handler"""
        return input('RESPONSE: ')
    
    cap = CAPInstance(
        start_now=True,
        message_callback=log_message,
        request_callback=request_input,
        response_callback=get_response
    )
    
    try:
        result = cap.execute("dc proffit")
        print(f"\nCommand completed: {result.success}")
        
    finally:
        cap.stop()
        log_file.close()
        print("Log written to cap_automation.log")


if __name__ == '__main__':
    import os
    from datetime import datetime
    
    print("CAP Automation Examples")
    print("Choose an example to run:\n")
    print("1. Basic usage")
    print("2. Context manager")
    print("3. Batch vs Macro")
    print("4. Multiple experiments")
    print("5. Error handling")
    print("6. Remote control socket")
    print("7. Custom callbacks")
    print("0. Exit")
    
    choice = input("\nEnter choice (1-7, 0 to exit): ").strip()
    
    examples = {
        '1': example_basic_usage,
        '2': example_context_manager,
        '3': example_batch_vs_macro,
        '4': example_multiple_experiments,
        '5': example_error_handling,
        '6': example_remote_control,
        '7': example_custom_callbacks,
    }
    
    if choice in examples:
        try:
            examples[choice]()
        except CAPCommandError as e:
            print(f"\n✗ CAP Command Error:")
            print(f"  Command: {e.command}")
            print(f"  Message: {str(e)}")
            if e.log_output:
                print(f"  Log excerpt: {e.log_output[:300]}")
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
    elif choice == '0':
        print("Goodbye!")
    else:
        print("Invalid choice")
