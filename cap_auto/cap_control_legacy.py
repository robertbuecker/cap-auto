import os
import glob
import time
from typing import *
from dataclasses import dataclass, field
import queue
import subprocess
from glob import glob
from datetime import datetime
import io
from warnings import warn
import re
import socket
import threading
import json

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
# Result Classes
# ============================================================================

@dataclass
class CAPCommandResult:
    """Result from executing a CAP command.
    
    Attributes:
        command: The command that was executed
        success: Whether the command succeeded
        log_output: Log output captured during command execution
        warnings: List of warning messages found in log (lines starting with '?')
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
        
        # Execute multiple commands efficiently
        cap.execute_macro([
            "dc proffit",
            "dc rrp",
            "xx saveub"
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
                 message_callback: Optional[Callable[[str], None]] = None,
                 request_callback: Optional[Callable[[str], None]] = None,
                 response_callback: Optional[Callable[[], Any]] = None):
        
        # Handle deprecated cap_folder parameter
        if cap_folder is not None:
            warn('cap_folder is deprecated and will be removed in a future version. Use max_cap_version and min_cap_version instead.', DeprecationWarning)
            ver = os.path.split(cap_folder)[-1].split('.')
            if len(ver) == 2:
                ver = (int(ver[-1]), 1000)
            elif len(ver) == 3:
                ver = (int(ver[-2]), int(ver[-1]))
            else:
                raise ValueError(f'Invalid CAP folder name {cap_folder}. Expected format CrysAlisPro171.x or CrysAlisPro171.x.y')
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
        
        # Command history
        self.history: List[CAPCommandResult] = []
        
        # Communication callbacks (for interactive workflows)
        self._message_func = message_callback or print
        self._request_func = request_callback or print
        self._response_func = response_callback or input
        
        # Socket server (optional remote control)
        self._socket_server: Optional[threading.Thread] = None
        self._socket_running = False
        
        # Setup
        os.makedirs(cmd_folder, exist_ok=True)
        
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
    # Helper Methods (Internal Use)
    # ========================================================================
    
    def _find_cap_installation(self, min_version, max_version) -> tuple[str, tuple]:
        """Find CAP installation matching version requirements."""
        cap_base_path = 'C:\\Xcalibur\\CrysAlisPro171'
        
        # Normalize version specifications
        if isinstance(max_version, str):
            max_version = tuple(int(n) for n in max_version.strip('a').split('.'))
        if isinstance(min_version, str):
            min_version = tuple(int(n) for n in min_version.strip('a').split('.'))
        
        if max_version is None:
            max_version = (1000, 1000)
        elif isinstance(max_version, int):
            max_version = (max_version, 1000)
        
        if min_version is None:
            min_version = (0, 0)
        elif isinstance(min_version, int):
            min_version = (min_version, 0)
        
        # Find all installed versions
        cap_versions = [tuple(int(n.strip('a')) for n in os.path.split(fn)[0].split('.')[-2:]) 
                        for fn in glob(cap_base_path + f'.*.*\\pro.exe')]
        
        # Select best version in range
        for ver in sorted(cap_versions, reverse=True):
            if ver >= min_version and ver <= max_version:
                self._message_func(f'Found suitable CAP version {ver[0]}.{ver[1]}')
                break
        else:
            raise RuntimeError(f'No suitable CAP version found in range {min_version} - {max_version}')
        
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
        for fn in glob(self._command_file_path('*')):
            try:
                os.remove(fn)
            except (FileNotFoundError, PermissionError):
                pass
    
    def _write_command(self, cmd: str):
        """Write command to command.in file."""
        with open(self._command_file_path('in'), 'w') as fh:
            fh.write(cmd)
    
    def _get_status(self) -> str:
        """Get current listen mode status."""
        if os.path.exists(self._command_file_path('busy')):
            return 'busy'
        elif os.path.exists(self._command_file_path('error')):
            return 'error'
        else:
            return 'idle'
    
        """Update the log handle to the latest log file. This is used to read the log file in a non-blocking way.
        """        
        # first, determine filename
        import locale
        saved = locale.setlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, 'C')
            red_log_fn = sorted(glob(
                os.path.join(os.path.dirname(self.par_file), 'log', 'crysalispro_redLOG*.txt')), 
                                reverse=True, key=os.path.getmtime)[0]
            timestamp = datetime.strptime(os.path.basename(red_log_fn), f'crysalispro_redLOG%a-%b-%d-%H-%M-%S-%Y.txt')
        except Exception as err:
            raise CAPListenModeError(f'Cannot find log file for experiment {self.par_file}')
        finally:
            locale.setlocale(locale.LC_ALL, saved)
            
        if self.log_handle is None:
            self.log_handle = open(red_log_fn, 'r')
        elif self.log_handle.name != red_log_fn:
            self.log_handle.close()
            self.log_handle = open(red_log_fn, 'r')
        
    def start_cap(self, timeout=20):    
        if self.running:
            raise CAPListenModeError('CAP instance is already running; cannot start one.')
                
        self.cap_proc = subprocess.Popen(f'{os.path.join(self.cap_folder, "pro.exe")} "{self.par_file}" -listenmode "{self.cmd_folder}"')
        t0 = time.time()
        while True:
            try:
                self.run_cmd('xx sleep 1', timeout=0.2)
                self.update_log_handle()
                break
            except CAPListenModeError as err:
                if time.time() > (t0 + timeout):
                    raise CAPListenModeError(f'CAP not reacting {timeout} seconds after launch. Please check if a CAP window is running and retry.')
        
    def stop_cap(self, allow_stopped: bool = False):

        if (not self.running or (self.cap_proc is None)) and (not allow_stopped):
            raise CAPListenModeError('No CAP instance running.')
        elif (not self.running or (self.cap_proc is None)):
            return
                
        try:
            self.run_cmd('xx listenmode off', timeout=1)
        except CAPListenModeError:
            pass
        finally:
            self.cap_proc.terminate()
            self.cap_proc = None
            self.log_handle = None
            
    def __del__(self):
        try:
            self.stop_cap(allow_stopped=True)
        except Exception as err:
            pass
        
    @property
    def status(self):
        listen_fn = lambda ext: os.path.join(self.cmd_folder, f'command.{ext}')      
        if os.path.exists(listen_fn('busy')):
            return('Busy')
        elif os.path.exists(listen_fn('error')):
            return('Error')
        else:
            return('Idle')
        
    @property
    def running(self):
        return (self.cap_proc is not None) and (self.cap_proc.poll() is None)
    
    def load_experiment(self, par_file: str):
        """Load experiment in CAP instance. This is required for any command that requires a loaded experiment.

        Args:
            par_file (str): Name of the experiment to load.
        """
        
        self.par_file = par_file
        if not os.path.exists(self.par_file):
            raise FileNotFoundError(f'Experiment {self.par_file} not found.')
        if self.running:
            self.run_cmd(f'xx selectexpnogui \"{self.par_file}\"') 
            self.update_log_handle()
            
    def run_cmd_multi_exp(self, cmd: Union[str, List[str]], 
                          par_files: Union[str, List[str]], use_mac: bool = True, 
                          timeout: Optional[float] = None, auto_start: bool = True):
        """Run a command on multiple experiments in the CAP instance."""
        if isinstance(par_files, str):
            par_files = [par_files] 
        
        for par_file in par_files:
            if not os.path.exists(par_file):
                raise FileNotFoundError(f'Experiment {par_file} not found.')
            self.load_experiment(par_file)
            self.run_cmd(cmd, use_mac=use_mac, timeout=timeout, auto_start=auto_start)
        
    def run_cmd(self, cmd: Union[str, List[str]], 
                use_mac: bool = True, 
                timeout: Optional[float] = None,
                auto_start: bool = True):        
        
        if auto_start and not self.running:
            self.start_cap()
        
        multi_cmd = isinstance(cmd, list) 
        macro = '\n'.join(cmd) if multi_cmd else ''
        listen_fn = lambda ext: os.path.join(self.cmd_folder, f'command.{ext}')      
        
        if self.status == 'Busy':
            raise CAPListenModeError('CAP Instance is busy. Cannot submit new command.')  
                
        for fn in glob(listen_fn('*')): 
            try:
                os.remove(fn)
            except FileNotFoundError as err:
                # file might not exist, e.g. if it was already removed by another CAP instance
                pass
               
        if multi_cmd and use_mac:
            # replace calls by macro call (will be faster for many little calls)
            with open(fn := listen_fn('mac'), 'w') as fh:
                fh.write(macro)
            cmd = f'script {fn}'
        elif multi_cmd:
            for the_cmd in cmd:
                self.run_cmd(the_cmd)
            return
                                
        with open(listen_fn('in'), 'w') as fh:
            fh.write(cmd)        
        self.last_command = cmd
            
        t0 = time.time()
        while not self.status == 'Busy':
            if (time.time() - t0) < self.start_timeout:
                time.sleep(0.01)
            else:
                raise CAPListenModeError(f'CAP listen mode not reacting in {self.cmd_folder}. If listen mode is not active, start it by running "xx listenmode on" in the CrysAlisPro CMD window.')
            
        t0 = time.time()
        while self.status == 'Busy':
            if not timeout or ((time.time() - t0) < timeout):
                time.sleep(0.01)
            else:
                with open(listen_fn('stop'), 'w') as fh:
                    pass
                raise CAPListenModeError(f'CAP command {cmd} timed out after {time.time()-t0:.2f} seconds.')
        
        while not self.status in ['Idle', 'Error']:
            # wait for command to finish
            time.sleep(0.01)        
                    
        if os.path.exists(fn := listen_fn('error')):
            with open(fn, 'r') as fh:
                cmd_ret = fh.read().strip()
            os.remove(fn)
            if cmd_ret.startswith('script'):
                # expand error message to macro
                with open(cmd_ret.split(maxsplit=1)[-1], 'r') as fh:
                    cmds_ret = fh.readlines()
                raise CAPCommandError(f'Failed CAP commands: \n{"".join(cmds_ret)}')
            else:
                raise CAPCommandError(f'Failed CAP command: \n{cmd_ret}')
                        
        elif os.path.exists(fn := listen_fn('done')):
            with open(fn, 'r') as fh:
                cmd_ret = fh.read().strip()
            os.remove(fn)
            if cmd == cmd_ret:
                # print(f'Command:\n{cmd_ret}\nfinished successfully.')
                pass
            else:
                raise CAPListenModeError(f'Returned command:\n{cmd_ret}\ndoes not match request:\n{cmd}')
            
        else:
            # this should never be reached, unless really bad timing conditions surface
            raise CAPListenModeError('Confirmation file not found.')

class CAPControl:
 
    def __init__(self, work_folder: str, cap_instance: CAPInstance,
                 message_func: Optional[Union[Callable[[str], None], queue.Queue]] = None,
                 request_func: Optional[Union[Callable[[str], None], queue.Queue]] = None,                 
                 response_func: Optional[Union[Callable[[], Any], queue.Queue]] = None):
        
        """Base class for Python-controlled CAP workflows, to be executed via macros or listen mode.
        Functions that run command sequences can be blocking, and should communicate to the outside (e.g. GUI) via queues.

        Args:
            work_folder (str): _description_
            cmd_folder (Optional[str], optional): _description_. Defaults to None.
            cap_instance (CAPInstance): Listen mode CAP instance
            message_func (Optional[Union[Callable[[str], None], queue.Queue]], optional): Function/queue via which info messages are sent. 
            If None, just prints messages. Defaults to None.
            request_func (Optional[Union[Callable[[str], None], queue.Queue]], optional): Function/queue via which requests are sent that require a response. 
            If None, just prints requests. Defaults to None.
            response_func (Optional[Union[Callable[[], Any], queue.Queue]], optional): Function/queue via which info responses are returned. 
            If None, reads from command line. Defaults to None.
        """
        #TODO check if this class is actually still required, or if it can be replaced by CAPInstance directly
        
        self._cap = cap_instance
        self.work_folder = work_folder
        
        if message_func is None:
            self._message_func = print
        elif isinstance(message_func, queue.Queue):
            self._message_func = message_func.put
        else:
            self._message_func = message_func
            
        if request_func is None:
            self._request_func = print
        elif isinstance(request_func, queue.Queue):
            self._request_func = request_func.put
        else:
            self._request_func = request_func
            
        if response_func is None:
            self._response_func = input
        elif isinstance(response_func, queue.Queue):
            self._response_func = response_func.get
        else:
            self._response_func = response_func                        

    def message(self, msg):
        self._message_func(msg)
            
    def request(self, prompt: Optional[str] = None):
        if prompt is not None:
            self._request_func(prompt)
        return self._response_func()
    
    def run(self, cmd, timeout: Optional[float] = None, **kwargs):
        try:
            self._cap.run_cmd(cmd, timeout=timeout, **kwargs)
            
        except CAPListenModeError as err:
            self.message(str(err))
            raise(err)
        

