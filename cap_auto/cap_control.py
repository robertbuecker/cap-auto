"""
CrysAlisPro Listen Mode Interface

A simple Python wrapper for controlling CrysAlisPro via its listen mode interface.
Designed for scientists familiar with CAP but with minimal Python expertise.

Author: Robert Buecker
Date: 2025
"""

import os
import glob
import time
import re
import subprocess
import socket
import threading
import json
import io
from typing import Union, Optional, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from warnings import warn
from glob import glob as glob_func

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

# ============================================================================
# Exception Classes
# ============================================================================

class CAPListenModeError(RuntimeError):
    """Raised when listen mode communication fails."""
    pass


class CAPCommandError(ValueError):
    """Raised when a CAP command fails with error status.
    
    Attributes:
        command: The command that failed
        log_output: Relevant log output around the error
        error_file_content: Content of command.error file if available
    """
    def __init__(self, message: str, command: str = '', log_output: str = '', error_file_content: str = ''):
        super().__init__(message)
        self.command = command
        self.log_output = log_output
        self.error_file_content = error_file_content


class CAPRuntimeError(RuntimeError):
    """Raised when a CAP runtime issue occurs."""
    pass


# ============================================================================
# Event Handler for Listen Mode (Watchdog Integration)
# ============================================================================

class ListenModeEventHandler(FileSystemEventHandler):
    """File system event handler for CAP listen mode status files.
    
    This handler monitors the listen mode folder for status file changes and
    uses threading.Event objects to signal state transitions, eliminating the
    need for polling loops.
    
    Status files monitored:
        - command.busy: Created when CAP picks up a command
        - command.done: Created when command completes successfully
        - command.error: Created when command fails
    
    Events signaled:
        - command_picked_up: Set when command.busy is created
        - command_completed: Set when command.busy is deleted
        - status_finalized: Set when command.done or command.error is created
    """
    
    def __init__(self, cmd_folder: str):
        super().__init__()
        self.cmd_folder = cmd_folder
        
        # Threading events for state transitions
        self.command_picked_up = threading.Event()
        self.command_completed = threading.Event()
        self.status_finalized = threading.Event()
        
        # Status tracking (thread-safe)
        self._status_lock = threading.Lock()
        self.current_status = 'idle'
        self.final_status: Optional[str] = None
        
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        
        if filename == 'command.busy':
            with self._status_lock:
                self.current_status = 'busy'
            self.command_picked_up.set()
        
        elif filename == 'command.done':
            with self._status_lock:
                self.current_status = 'idle'
                self.final_status = 'done'
            self.status_finalized.set()
        
        elif filename == 'command.error':
            with self._status_lock:
                self.current_status = 'error'
                self.final_status = 'error'
            self.status_finalized.set()
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        
        if filename == 'command.busy':
            # Busy file deleted - command is completing
            self.command_completed.set()
    
    def get_status(self) -> str:
        """Get current status (thread-safe)."""
        with self._status_lock:
            return self.current_status
    
    def reset(self):
        """Reset events for next command execution."""
        self.command_picked_up.clear()
        self.command_completed.clear()
        self.status_finalized.clear()
        with self._status_lock:
            self.final_status = None
            # Don't reset current_status - it reflects actual state


# ============================================================================
# Result Classes
# ============================================================================

@dataclass
class CAPCommandResult:
    """Result from executing a CAP command.
    
    Attributes:
        command: The command that was executed
        success: Whether the command succeeded
        log_output: Log output captured during command execution
        warnings: List of warning messages found in log
        errors: List of error messages found in log
        execution_time: Time taken to execute the command in seconds
    """
    command: str
    success: bool
    log_output: str = ''
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    def has_warnings(self) -> bool:
        """Check if command produced warnings."""
        return len(self.warnings) > 0
    
    def has_errors(self) -> bool:
        """Check if command produced errors."""
        return len(self.errors) > 0


# ============================================================================
# Main CAP Instance Class
# ============================================================================

class CAPInstance:
    """Interface to control CrysAlisPro via listen mode.
    
    This class provides a thin Python wrapper around CAP's listen mode interface,
    making it easy to automate CAP workflows while keeping the interface simple
    for scientists who know CAP but may not be expert Python programmers.
    
    Basic usage:
        # Create and start CAP instance
        cap = CAPInstance(start_now=True)
        
        # Execute single command
        result = cap.execute("dc proffit")
        if result.success:
            print("Data reduction completed")
            print(result.log_output)
        
        # Execute multiple commands efficiently with macro
        cap.execute_macro([
            "dc proffit",
            "dc rrp",
            "xx saveub"
        ])
        
        # Execute batch without macro (individual commands)
        cap.execute_batch([
            "gt o 0",
            "gt k 90", 
            "gt p 0"
        ])
        
        # Load different experiment
        cap.load_experiment("path/to/experiment.par")
        
        # Clean shutdown
        cap.stop()
    
    Optional context manager usage:
        with CAPInstance() as cap:
            cap.execute("dc proffit")
        # Automatically stops CAP on exit
    
    Args:
        max_cap_version: Maximum CAP version to use (int, tuple, or string like "44.1")
        min_cap_version: Minimum CAP version to use  
        cmd_folder: Folder for listen mode command files
        par_file: Initial experiment .par file to load (optional)
        start_now: If True, start CAP immediately on creation
        error_patterns: List of regex patterns to identify errors in log output
                       Default: [r'^\\?.*', r'^ERROR:', r'^FATAL:']
        warning_patterns: List of regex patterns to identify warnings in log
                         Default: [r'^\\?.*', r'^WARNING:']
        raise_on_error: If True, raise CAPCommandError when command fails (default: True)
        raise_on_warning: If True, raise CAPCommandError when warnings detected (default: False)
        message_callback: Optional function to receive info messages (signature: str -> None)
        request_callback: Optional function to send requests (signature: str -> None) 
        response_callback: Optional function to get responses (signature: () -> Any)
    """
    
    def __init__(self, 
                 max_cap_version: Union[int, tuple, str] = 100,
                 min_cap_version: Union[int, tuple, str] = 44,
                 cmd_folder: str = 'C:\\Xcalibur\\tmp\\listen_mode_offline', 
                 par_file: Optional[str] = None, 
                 cap_folder: Optional[str] = None,
                 start_now: bool = False,
                 error_patterns: Optional[List[str]] = None,
                 warning_patterns: Optional[List[str]] = None,
                 raise_on_error: bool = True,
                 raise_on_warning: bool = False,
                 message_callback: Optional[Callable[[str], None]] = None,
                 request_callback: Optional[Callable[[str], None]] = None,
                 response_callback: Optional[Callable[[], Any]] = None):
        
        # Handle deprecated cap_folder parameter
        if cap_folder is not None:
            warn('cap_folder is deprecated. Use max_cap_version and min_cap_version instead.', 
                 DeprecationWarning, stacklevel=2)
            ver = os.path.split(cap_folder)[-1].split('.')
            if len(ver) == 2:
                ver = (int(ver[-1]), 1000)
            elif len(ver) == 3:
                ver = (int(ver[-2]), int(ver[-1]))
            else:
                raise ValueError(f'Invalid CAP folder: {cap_folder}')
        else:
            # Find suitable CAP version
            cap_folder, ver = self._find_cap_installation(min_cap_version, max_cap_version)
        
        # Core attributes
        self.cmd_folder = cmd_folder
        self.cap_folder = cap_folder  
        self.cap_version = ver       
        self.par_file = os.path.join(cap_folder, 'help', 'ideal_microed', 'MicroED.par') if par_file is None else par_file
        self.cap_proc: Optional[subprocess.Popen] = None
        self.start_timeout = 3
        
        # Log handling
        self.log_file: Optional[str] = None
        self.log_position: int = 0
        self._log_handle: Optional[io.TextIOWrapper] = None
        
        # Error/warning pattern matching
        self.error_patterns = error_patterns or [r'^\?.*', r'^ERROR:', r'^FATAL:']
        self.warning_patterns = warning_patterns or [r'^\?.*', r'^WARNING:']
        self._error_regex = [re.compile(p, re.MULTILINE) for p in self.error_patterns]
        self._warning_regex = [re.compile(p, re.MULTILINE) for p in self.warning_patterns]
        self.raise_on_error = raise_on_error
        self.raise_on_warning = raise_on_warning
        
        # Command history
        self.history: List[CAPCommandResult] = []
        
        # Communication callbacks (for interactive workflows)
        self._message_func = message_callback or print
        self._request_func = request_callback or print
        self._response_func = response_callback or input
        
        # Socket server (optional remote control)
        self._socket_server: Optional[threading.Thread] = None
        self._socket_running = False
        self._socket_port: Optional[int] = None
        
        # Watchdog file system observer (event-driven status monitoring)
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[ListenModeEventHandler] = None
        self._use_watchdog = WATCHDOG_AVAILABLE
        
        # Setup
        os.makedirs(cmd_folder, exist_ok=True)
        
        # Start watchdog observer if available
        if self._use_watchdog:
            self._event_handler = ListenModeEventHandler(cmd_folder)
            self._observer = Observer()
            self._observer.schedule(self._event_handler, cmd_folder, recursive=False)
            self._observer.start()
        
        # Try to stop any existing listen mode in this folder
        try:
            self._write_command('xx listenmode off')
            time.sleep(0.2)
            self._cleanup_command_files()
        except:
            pass
        
        if start_now:
            self.start()
    
    # ========================================================================
    # Context Manager Support (Optional Usage Pattern)
    # ========================================================================
    
    def __enter__(self):
        """Enter context manager - start CAP if not already running."""
        if not self.is_running():
            self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - stop CAP."""
        self.stop(allow_stopped=True)
        return False
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.stop(allow_stopped=True)
        except:
            pass
        
        # Stop watchdog observer
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=1)
            except:
                pass
    
    # ========================================================================
    # Properties
    # ========================================================================
    
    def is_running(self) -> bool:
        """Check if CAP process is running."""
        return (self.cap_proc is not None) and (self.cap_proc.poll() is None)
    
    def get_status(self) -> str:
        """Get current listen mode status: 'idle', 'busy', or 'error'.
        
        Uses event handler if watchdog is available, otherwise falls back to
        polling filesystem.
        """
        if self._use_watchdog and self._event_handler:
            return self._event_handler.get_status()
        else:
            # Fallback to filesystem polling
            if os.path.exists(self._command_file_path('busy')):
                return 'busy'
            elif os.path.exists(self._command_file_path('error')):
                return 'error'
            else:
                return 'idle'
    
    # ========================================================================
    # Lifecycle Methods
    # ========================================================================
    
    def start(self, timeout: float = 20):
        """Start CAP process in listen mode.
        
        Args:
            timeout: Maximum seconds to wait for CAP to respond
            
        Raises:
            CAPListenModeError: If CAP doesn't start within timeout
        """
        if self.is_running():
            raise CAPListenModeError('CAP instance is already running')
        
        # Launch CAP in listen mode
        cmd = f'"{os.path.join(self.cap_folder, "pro.exe")}" "{self.par_file}" -listenmode "{self.cmd_folder}" '
        self.cap_proc = subprocess.Popen(cmd, shell=True)
        
        # Wait for CAP to be ready
        t0 = time.time()
        while True:
            try:
                result = self.execute('xx sleep 1', timeout=0.5, raise_on_error=False)
                if result.success:
                    self._update_log_file()
                    self._message_func(f'CAP started successfully (v{self.cap_version[0]}.{self.cap_version[1]})')
                    break
            except CAPListenModeError:
                pass
            
            if time.time() > (t0 + timeout):
                raise CAPListenModeError(
                    f'CAP not responding after {timeout}s. Check if CAP window appeared.')
            time.sleep(0.1)
    
    def stop(self, allow_stopped: bool = False):
        """Stop CAP process.
        
        Args:
            allow_stopped: If True, don't raise error if CAP already stopped
            
        Raises:
            CAPListenModeError: If CAP not running and allow_stopped=False
        """
        if not self.is_running():
            if not allow_stopped:
                raise CAPListenModeError('No CAP instance running')
            return
        
        # Try graceful shutdown
        try:
            self.execute('xx listenmode off', timeout=1, raise_on_error=False)
        except:
            pass
        
        # Force termination
        try:
            self.cap_proc.terminate()
            self.cap_proc.wait(timeout=5)
        except:
            self.cap_proc.kill()
        
        self._message_func('CAP stopped')
    
    # ========================================================================
    # Experiment Management
    # ========================================================================
    
    def load_experiment(self, par_file: str):
        """Load a different experiment into CAP.
        
        Args:
            par_file: Path to .par file
            
        Raises:
            FileNotFoundError: If par file doesn't exist
        """
        if not os.path.exists(par_file):
            raise FileNotFoundError(f'Experiment file not found: {par_file}')
        
        self.par_file = par_file
        
        if self.is_running():
            # Execute the load command (will capture old log)
            result = self.execute(f'xx selectexpnogui "{self.par_file}"')
            
            # Update to new experiment's log file
            self._update_log_file()
            
            # Replace log output with content from new experiment's log
            # (which is always fresh/new when loading, so read from start)
            time.sleep(0.1)  # Small delay for log to be written
            new_log = self._read_log_since(0)  # Read from start of new log
            result.log_output = new_log
            
            # Re-parse warnings/errors from new log
            result.warnings = self._find_pattern_matches(new_log, self._warning_regex)
            result.errors = self._find_pattern_matches(new_log, self._error_regex)
            
            self._message_func(f'Loaded experiment: {os.path.basename(par_file)}')
            return result
    
    # ========================================================================
    # Command Execution Methods (Primary Interface)
    # ========================================================================
    
    def execute(self, cmd: str, timeout: Optional[float] = None, 
                raise_on_error: Optional[bool] = None) -> CAPCommandResult:
        """Execute a single CAP command and return result.
        
        This is the primary method for executing CAP commands. The command
        is sent to CAP via listen mode, and the result including log output
        is captured and returned.
        
        Uses event-driven file monitoring (watchdog) when available for instant
        response. Falls back to polling if watchdog is not installed.
        
        Args:
            cmd: CAP command string (e.g., "dc proffit", "gt o 90")
            timeout: Maximum seconds to wait for command (None = no timeout)
            raise_on_error: Override instance setting for error handling
            
        Returns:
            CAPCommandResult with command outcome and log output
            
        Raises:
            CAPListenModeError: If listen mode communication fails
            CAPCommandError: If command fails and raise_on_error=True
            
        Example:
            result = cap.execute("dc proffit")
            if result.success:
                print("Data reduction completed")
                if result.has_warnings():
                    print(f"Warnings: {result.warnings}")
        """
        if not self.is_running():
            self.start()
        
        start_time = time.time()
        raise_on_error = raise_on_error if raise_on_error is not None else self.raise_on_error
        
        # Prepare for command
        if self.get_status() == 'busy':
            raise CAPListenModeError('CAP is busy with another command')
        
        self._cleanup_command_files()
        
        # Record log position before command
        log_start_pos = self._get_log_position()
        
        # Reset event handler for this command (if using watchdog)
        if self._use_watchdog and self._event_handler:
            self._event_handler.reset()
        
        # Write and send command
        self._write_command(cmd)
        
        # Wait for CAP to pick up command (event-driven or polling)
        if self._use_watchdog and self._event_handler:
            # Event-driven: wait for command_picked_up event
            if not self._event_handler.command_picked_up.wait(timeout=self.start_timeout):
                raise CAPListenModeError(
                    f'CAP did not pick up command within {self.start_timeout}s. Check listen mode is active.')
        else:
            # Fallback: polling
            t0 = time.time()
            while self.get_status() != 'busy':
                if (time.time() - t0) > self.start_timeout:
                    raise CAPListenModeError(
                        f'CAP did not pick up command. Check listen mode is active.')
                time.sleep(0.01)
        
        # Wait for command to complete (event-driven or polling)
        if self._use_watchdog and self._event_handler:
            # Event-driven: wait for command_completed event
            if timeout:
                elapsed = time.time() - start_time
                remaining_timeout = timeout - elapsed
                if remaining_timeout <= 0:
                    raise CAPListenModeError(f'Command timed out before completion: {cmd}')
            else:
                remaining_timeout = None
            
            if not self._event_handler.command_completed.wait(timeout=remaining_timeout):
                # Timeout - send stop signal
                try:
                    with open(self._command_file_path('stop'), 'w') as fh:
                        fh.write('')
                except:
                    pass
                raise CAPListenModeError(f'Command timed out after {timeout}s: {cmd}')
        else:
            # Fallback: polling
            t0 = time.time()
            while self.get_status() == 'busy':
                if timeout and ((time.time() - t0) > timeout):
                    # Timeout - send stop signal
                    with open(self._command_file_path('stop'), 'w') as fh:
                        fh.write('')
                    raise CAPListenModeError(f'Command timed out after {timeout}s: {cmd}')
                time.sleep(0.01)
        
        # Wait for final status file (event-driven or polling)
        if self._use_watchdog and self._event_handler:
            # Event-driven: wait for status_finalized event
            if not self._event_handler.status_finalized.wait(timeout=2.0):
                # Fallback to checking filesystem if event doesn't arrive
                self._message_func('Warning: Status finalization event timeout, checking filesystem')
        else:
            # Fallback: polling
            while self.get_status() not in ['idle', 'error']:
                time.sleep(0.01)
        
        # Process result
        success = True
        error_content = ''
        
        if os.path.exists(self._command_file_path('error')):
            success = False
            with open(self._command_file_path('error'), 'r') as fh:
                error_content = fh.read().strip()
            os.remove(self._command_file_path('error'))
        
        elif os.path.exists(self._command_file_path('done')):
            with open(self._command_file_path('done'), 'r') as fh:
                returned_cmd = fh.read().strip()
            os.remove(self._command_file_path('done'))
            
            if returned_cmd != cmd:
                self._message_func(f'Warning: Command mismatch: sent "{cmd}", got "{returned_cmd}"')
        
        # Capture log output
        log_output = self._read_log_since(log_start_pos)
        
        # Parse warnings and errors from log
        warnings = self._find_pattern_matches(log_output, self._warning_regex)
        errors = self._find_pattern_matches(log_output, self._error_regex)
        
        execution_time = time.time() - start_time
        
        # Create result
        result = CAPCommandResult(
            command=cmd,
            success=success,
            log_output=log_output,
            warnings=warnings,
            errors=errors,
            execution_time=execution_time
        )
        
        self.history.append(result)
        
        # Handle errors/warnings
        if not success:
            msg = f'Command failed: {cmd}\nError: {error_content}'
            if raise_on_error:
                raise CAPCommandError(msg, command=cmd, log_output=log_output, 
                                     error_file_content=error_content)
            else:
                self._message_func(f'Warning: {msg}')
        
        elif errors and raise_on_error:
            msg = f'Command completed with errors: {cmd}\nErrors: {errors}'
            raise CAPCommandError(msg, command=cmd, log_output=log_output)
        
        elif warnings and self.raise_on_warning:
            msg = f'Command completed with warnings: {cmd}\nWarnings: {warnings}'
            raise CAPCommandError(msg, command=cmd, log_output=log_output)
        
        return result
    
    def execute_batch(self, commands: List[str], timeout: Optional[float] = None,
                     stop_on_error: bool = True) -> List[CAPCommandResult]:
        """Execute multiple commands sequentially (not as macro).
        
        Commands are executed one by one, with individual results captured.
        This is slower than execute_macro but provides better error tracking.
        
        Args:
            commands: List of CAP command strings
            timeout: Maximum seconds per command (None = no timeout)
            stop_on_error: If True, stop on first error
            
        Returns:
            List of CAPCommandResult for each command
            
        Example:
            results = cap.execute_batch([
                "gt o 0",
                "gt k 90",
                "gt p 0"
            ])
            for r in results:
                print(f"{r.command}: {'OK' if r.success else 'FAILED'}")
        """
        results = []
        
        for cmd in commands:
            try:
                result = self.execute(cmd, timeout=timeout, raise_on_error=stop_on_error)
                results.append(result)
                
                if not result.success and stop_on_error:
                    break
                    
            except CAPCommandError as e:
                # Error already logged, re-raise if stop_on_error
                if stop_on_error:
                    raise
                else:
                    # Create failed result
                    results.append(CAPCommandResult(
                        command=cmd,
                        success=False,
                        log_output=e.log_output,
                        errors=[str(e)]
                    ))
        
        return results
    
    def execute_macro(self, commands: List[str], timeout: Optional[float] = None) -> CAPCommandResult:
        """Execute multiple commands as a macro (fast but harder error tracking).
        
        Commands are written to a .mac file and executed by CAP as a script.
        This is much faster for many commands but makes it harder to pinpoint
        which specific command failed. The log is parsed to identify failures.
        
        Args:
            commands: List of CAP command strings
            timeout: Maximum seconds for entire macro (None = no timeout)
            
        Returns:
            CAPCommandResult for the macro execution
            
        Raises:
            CAPCommandError: If any command in macro fails
            
        Example:
            result = cap.execute_macro([
                "dc proffit",
                "dc rrp", 
                "xx saveub"
            ])
        """
        if not self.is_running():
            self.start()
        
        # Write macro file
        macro_path = self._command_file_path('mac')
        with open(macro_path, 'w') as fh:
            fh.write('\n'.join(commands))
        
        # Execute script command
        script_cmd = f'script {macro_path}'
        result = self.execute(script_cmd, timeout=timeout)
        
        # If failed, try to identify which command failed
        if not result.success:
            # Parse log to find failed command
            failed_cmd = self._find_failed_command_in_macro(result.log_output, commands)
            if failed_cmd:
                result.command = f'Macro failed at: {failed_cmd}'
        
        return result
    
    def execute_on_multiple_experiments(self, commands: Union[str, List[str]], 
                                       par_files: List[str],
                                       use_macro: bool = True) -> List[CAPCommandResult]:
        """Execute command(s) on multiple experiments.
        
        Args:
            commands: Single command string or list of commands
            par_files: List of .par files to process
            use_macro: If True and commands is list, use macro for speed
            
        Returns:
            List of CAPCommandResult (one per experiment)
            
        Example:
            results = cap.execute_on_multiple_experiments(
                "dc proffit",
                ["exp1.par", "exp2.par", "exp3.par"]
            )
        """
        if isinstance(commands, str):
            commands = [commands]
        
        results = []
        
        for par_file in par_files:
            self.load_experiment(par_file)
            
            if use_macro and len(commands) > 1:
                result = self.execute_macro(commands)
            elif len(commands) == 1:
                result = self.execute(commands[0])
            else:
                batch_results = self.execute_batch(commands)
                # Combine into single result
                result = CAPCommandResult(
                    command=f'Batch: {len(commands)} commands',
                    success=all(r.success for r in batch_results),
                    log_output='\n'.join(r.log_output for r in batch_results),
                    execution_time=sum(r.execution_time for r in batch_results)
                )
            
            results.append(result)
        
        return results
    
    # ========================================================================
    # Communication Methods (For Interactive Workflows)
    # ========================================================================
    
    def message(self, msg: str):
        """Send a message via the message callback."""
        self._message_func(msg)
    
    def request(self, prompt: Optional[str] = None) -> Any:
        """Send a request and get response via callbacks.
        
        Args:
            prompt: Optional prompt to display
            
        Returns:
            Response from response_callback
        """
        if prompt:
            self._request_func(prompt)
        return self._response_func()
    
    # ========================================================================
    # Socket Server (For Remote Control)
    # ========================================================================
    
    def start_socket_server(self, port: int = 0, host: str = 'localhost'):
        """Start TCP socket server for remote control.
        
        The socket server accepts JSON commands and returns JSON responses.
        
        Command format:
            {"command": "dc proffit", "timeout": 60}
        
        Response format:
            {"success": true, "log_output": "...", "warnings": [], "errors": []}
        
        Args:
            port: Port number (0 = auto-select)
            host: Host to bind to
            
        Returns:
            Actual port number used
            
        Example:
            port = cap.start_socket_server(9000)
            print(f"Remote control available on port {port}")
        """
        if self._socket_running:
            raise RuntimeError('Socket server already running')
        
        self._socket_running = True
        self._socket_server = threading.Thread(
            target=self._socket_server_thread,
            args=(port, host),
            daemon=True
        )
        self._socket_server.start()
        
        # Wait for server to start and get port
        time.sleep(0.1)
        return self._socket_port
    
    def stop_socket_server(self):
        """Stop the socket server."""
        self._socket_running = False
        if self._socket_server:
            self._socket_server.join(timeout=2)
            self._socket_server = None
    
    def _socket_server_thread(self, port: int, host: str):
        """Socket server thread function."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(1)
            server.settimeout(1.0)
            
            # Store actual port
            self._socket_port = server.getsockname()[1]
            self._message_func(f'Socket server listening on {host}:{self._socket_port}')
        except PermissionError as e:
            self._message_func(f'ERROR: Cannot bind to port {port} - Permission denied')
            self._message_func(f'  This may be due to Windows firewall or port already in use')
            self._message_func(f'  Try: 1) Different port, 2) Run as admin, 3) Check firewall')
            self._message_func(f'  Windows error: {e}')
            self._socket_running = False
            self._socket_port = None
            return
        except OSError as e:
            self._message_func(f'ERROR: Cannot start socket server on port {port}')
            self._message_func(f'  Error: {e}')
            self._socket_running = False
            self._socket_port = None
            return
        
        while self._socket_running:
            try:
                client, addr = server.accept()
                client.settimeout(1.0)
                self._message_func(f'Client connected from {addr}')
                
                # Handle client in separate thread
                threading.Thread(
                    target=self._handle_socket_client,
                    args=(client,),
                    daemon=True
                ).start()
                
            except socket.timeout:
                continue
            except Exception as e:
                self._message_func(f'Socket server error: {e}')
        
        server.close()
        self._message_func('Socket server stopped')
    
    def _handle_socket_client(self, client: socket.socket):
        """Handle commands from a socket client."""
        try:
            # Receive command (JSON)
            data = b''
            while self._socket_running:
                try:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b'\n' in data:
                        break
                except socket.timeout:
                    continue
            
            if not data:
                return
            
            # Parse command
            cmd_data = json.loads(data.decode('utf-8'))
            command = cmd_data.get('command', '')
            timeout = cmd_data.get('timeout')
            
            # Execute command
            try:
                result = self.execute(command, timeout=timeout, raise_on_error=False)
                response = {
                    'success': result.success,
                    'log_output': result.log_output,
                    'warnings': result.warnings,
                    'errors': result.errors,
                    'execution_time': result.execution_time
                }
            except Exception as e:
                response = {
                    'success': False,
                    'error': str(e)
                }
            
            # Send response
            response_json = json.dumps(response) + '\n'
            client.sendall(response_json.encode('utf-8'))
            
        except Exception as e:
            self._message_func(f'Client handler error: {e}')
        finally:
            client.close()
    
    # ========================================================================
    # Helper Methods (Internal Use)
    # ========================================================================
    
    def _find_cap_installation(self, min_version, max_version) -> tuple:
        """Find CAP installation matching version requirements."""
        cap_base_path = 'C:\\Xcalibur\\CrysAlisPro171'
        
        # Normalize version specifications
        if isinstance(max_version, str):
            max_version = tuple(int(n) for n in max_version.strip('a').split('.'))
        if isinstance(min_version, str):
            min_version = tuple(int(n) for n in min_version.strip('a').split('.'))
        
        if isinstance(max_version, int):
            max_version = (max_version, 1000)
        if isinstance(min_version, int):
            min_version = (min_version, 0)
        
        # Find all installed versions
        cap_versions = []
        for fn in glob_func(cap_base_path + '.*.*\\pro.exe'):
            try:
                parts = os.path.split(fn)[0].split('.')[-2:]
                ver = tuple(int(n.strip('a')) for n in parts)
                cap_versions.append(ver)
            except:
                pass
        
        # Select best version in range
        for ver in sorted(cap_versions, reverse=True):
            if ver >= min_version and ver <= max_version:
                break
        else:
            raise RuntimeError(
                f'No suitable CAP version found (need {min_version[0]}.{min_version[1]} - {max_version[0]}.{max_version[1]})')
        
        # Find actual folder with potential suffix
        for suffix in ['', 't', 'a', 'aa']:
            cap_folder = cap_base_path + f'.{ver[0]}.{ver[1]}{suffix}'
            if os.path.exists(os.path.join(cap_folder, 'pro.exe')):
                return cap_folder, ver
        
        raise FileNotFoundError(f'No CAP folder found for version {ver[0]}.{ver[1]}')
    
    def _command_file_path(self, ext: str) -> str:
        """Get path to listen mode command file with given extension."""
        return os.path.join(self.cmd_folder, f'command.{ext}')
    
    def _cleanup_command_files(self):
        """Remove all command.* files from listen mode folder."""
        for fn in glob_func(self._command_file_path('*')):
            try:
                os.remove(fn)
            except (FileNotFoundError, PermissionError):
                pass
    
    def _write_command(self, cmd: str):
        """Write command to command.in file."""
        with open(self._command_file_path('in'), 'w') as fh:
            fh.write(cmd)
    
    def _update_log_file(self):
        """Update log file path and handle to current experiment log."""
        import locale
        saved = locale.setlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, 'C')
            log_dir = os.path.join(os.path.dirname(self.par_file), 'log')
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                return
            
            log_files = glob_func(os.path.join(log_dir, 'crysalispro_redLOG*.txt'))
            if not log_files:
                return
            
            latest_log = sorted(log_files, key=os.path.getmtime, reverse=True)[0]
            
            if self.log_file != latest_log:
                # New log file
                if self._log_handle:
                    self._log_handle.close()
                self.log_file = latest_log
                self.log_position = 0
                self._log_handle = None
                
        except Exception as e:
            self._message_func(f'Warning: Cannot access log file: {e}')
        finally:
            locale.setlocale(locale.LC_ALL, saved)
    
    def _get_log_position(self) -> int:
        """Get current position in log file."""
        if not self.log_file or not os.path.exists(self.log_file):
            self._update_log_file()
        
        if self.log_file and os.path.exists(self.log_file):
            return os.path.getsize(self.log_file)
        return 0
    
    def _read_log_since(self, start_pos: int) -> str:
        """Read log file content since given position."""
        if not self.log_file or not os.path.exists(self.log_file):
            return ''
        
        try:
            # Ensure we have fresh data
            time.sleep(0.1)
            
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as fh:
                fh.seek(start_pos)
                content = fh.read()
            
            return content
        except Exception as e:
            self._message_func(f'Warning: Error reading log: {e}')
            return ''
    
    def _find_pattern_matches(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """Find all lines matching any of the given regex patterns."""
        matches = []
        for line in text.split('\n'):
            for pattern in patterns:
                if pattern.search(line):
                    matches.append(line.strip())
                    break
        return matches
    
    def _find_failed_command_in_macro(self, log_output: str, commands: List[str]) -> Optional[str]:
        """Try to identify which command failed in a macro from log output."""
        # Look for command echoes in log
        for cmd in commands:
            # Commands often appear in log with '>' prefix or in error messages
            if f'>{cmd}' in log_output or cmd in log_output:
                # Check if followed by error indicators
                cmd_pos = log_output.find(cmd)
                after_cmd = log_output[cmd_pos:cmd_pos+200]
                if any(err in after_cmd.lower() for err in ['error', 'failed', 'fatal', '?']):
                    return cmd
        return None

class CAPInstanceOnline(CAPInstance):
    """CAPInstance subclass with online instrument operation. Instead of launching CAP, it connects
    to an existing CAP instance controlling the instrument.
    """
    
    def __init__(self, cmd_folder: str = 'C:\\Xcalibur\\tmp\\listen_mode', start_now=False, **kwargs):
        
        # Override start to not launch CAP but to attach to existing instance
        self.start = self._attach_online
        self.stop = self._detach_online
        self._is_running_online = False # we need to track this separately as we do not own the CAP process
        self.cap_folder = None # unknown
        self.cap_version = None # unknown
        super().__init__(cmd_folder=cmd_folder, start_now=start_now, **kwargs)
        
    def is_running(self) -> bool:
        # overloading to track online status
        return self._is_running_online

    def _attach_online(self, timeout: float = 20):
        """Attach to existing CAP instance in listen mode."""
        if self.is_running():
            raise CAPListenModeError('CAP instance is already running')
        
        # Wait for CAP to be ready
        t0 = time.time()
        self._is_running_online = True # required here to avoid infinite recursion in `execute`
        
        while True:
            try:
                result = self.execute('xx sleep 1', timeout=0.5, raise_on_error=False)
                if result.success:
                    self._update_log_file()
                    self._message_func(f'Attached to online CAP instance.')
                    break
            except CAPListenModeError:
                pass
            
            if time.time() > (t0 + timeout):
                self._is_running_online = False
                raise CAPListenModeError(
                    f'CAP not responding after {timeout}s. Ensure CAP is running in listen mode.')
            time.sleep(0.1)
        
    def _detach_online(self, allow_stopped: bool = False):
        """Detach from online CAP instance."""
        if not self.is_running():
            if not allow_stopped:
                raise CAPListenModeError('No CAP instance running')
            return
        
        try:
            self.execute('xx listenmode off', timeout=1, raise_on_error=False)
        except:
            pass
        
        self._is_running_online = False
        self._message_func('Detached from online CAP instance.')

    def _update_log_file(self):
        """Update the log file path and version information for online CAP from global log folder"""
        import locale
        saved = locale.setlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, 'C')
            log_dir = os.path.join('C:\\Xcalibur\\log')
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                return
            
            log_files = glob_func(os.path.join(log_dir, 'crysalispro_ccdLOG*.txt'))
            if not log_files:
                return
            
            latest_log = sorted(log_files, key=os.path.getmtime, reverse=True)[0]
            
            if self.log_file != latest_log:
                # New log file
                if self._log_handle:
                    self._log_handle.close()
                self.log_file = latest_log
                self.log_position = 0
                self._log_handle = None
                
        except Exception as e:
            self._message_func(f'Warning: Cannot access log file: {e}')
        finally:
            locale.setlocale(locale.LC_ALL, saved)

# ============================================================================
# Backward Compatibility (Deprecated)
# ============================================================================

class CAPControl:
    """Deprecated class - use CAPInstance directly instead.
    
    This class is kept for backward compatibility but will be removed
    in a future version. All functionality has been merged into CAPInstance.
    """
    
    def __init__(self, work_folder: str, cap_instance: CAPInstance, **kwargs):
        warn('CAPControl is deprecated. Use CAPInstance directly.', 
             DeprecationWarning, stacklevel=2)
        self._cap = cap_instance
        self.work_folder = work_folder
    
    def message(self, msg):
        self._cap.message(msg)
    
    def request(self, prompt=None):
        return self._cap.request(prompt)
    
    def run(self, cmd, timeout=None, **kwargs):
        """Deprecated - use cap.execute() instead."""
        return self._cap.execute(cmd, timeout=timeout)
