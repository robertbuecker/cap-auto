"""
CAP Socket Client GUI

Simple Tkinter GUI to send commands to a CAP socket server.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import json
import threading

class CAPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAP Socket Client")
        self.root.geometry("700x600")
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Connection configuration frame
        conn_frame = ttk.LabelFrame(self.root, text="Server", padding=10)
        conn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky='w', padx=5)
        self.host_var = tk.StringVar(value="localhost")
        ttk.Entry(conn_frame, textvariable=self.host_var, width=20).grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky='w', padx=5)
        self.port_var = tk.StringVar(value="9005")
        self.port_entry = ttk.Entry(conn_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=3, sticky='w', padx=5)
        
        ttk.Label(conn_frame, text="(Reconnects for each command)").grid(row=0, column=4, sticky='w', padx=10)
        
        # Command frame
        cmd_frame = ttk.LabelFrame(self.root, text="Command", padding=10)
        cmd_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(cmd_frame, text="CAP Command:").grid(row=0, column=0, sticky='w', padx=5)
        self.command_var = tk.StringVar(value="dc proffit")
        self.command_entry = ttk.Entry(cmd_frame, textvariable=self.command_var, width=50)
        self.command_entry.grid(row=0, column=1, sticky='ew', padx=5)
        self.command_entry.bind('<Return>', lambda e: self._send_command())
        
        ttk.Label(cmd_frame, text="Timeout (s):").grid(row=1, column=0, sticky='w', padx=5)
        self.timeout_var = tk.StringVar(value="60")
        ttk.Entry(cmd_frame, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky='w', padx=5)
        
        self.send_button = ttk.Button(cmd_frame, text="SEND COMMAND", command=self._send_command, state='disabled')
        self.send_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        cmd_frame.columnconfigure(1, weight=1)
        
        # Response frame
        response_frame = ttk.LabelFrame(self.root, text="Response (JSON)", padding=10)
        response_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.response_text = scrolledtext.ScrolledText(response_frame, wrap=tk.WORD, height=20, font=('Courier', 10))
        self.response_text.pack(fill='both', expand=True)
        
        # Command history
        history_frame = ttk.LabelFrame(self.root, text="Recent Commands", padding=5)
        history_frame.pack(fill='x', padx=10, pady=5)
        
        self.history_listbox = tk.Listbox(history_frame, height=3)
        self.history_listbox.pack(fill='x')
        self.history_listbox.bind('<<ListboxSelect>>', self._on_history_select)
        
    def _log(self, message):
        """Add message to response text"""
        self.response_text.insert(tk.END, message + '\n')
        self.response_text.see(tk.END)
        
    def _send_command(self):
        """Send command to server"""
        command = self.command_var.get().strip()
        if not command:
            messagebox.showerror("Error", "Command cannot be empty")
            return
        
        try:
            timeout = float(self.timeout_var.get())
        except ValueError:
            messagebox.showerror("Error", "Timeout must be a number")
            return
        
        # Add to history
        self.history_listbox.insert(0, command)
        if self.history_listbox.size() > 10:
            self.history_listbox.delete(10, tk.END)
        
        self._log("\n" + "=" * 60)
        self._log(f"Sending command: {command}")
        self._log(f"Timeout: {timeout}s")
        self._log("-" * 60)
        
        # Disable send button
        self.send_button.config(state='disabled')
        
        # Send in background thread
        thread = threading.Thread(target=self._send_command_thread, args=(command, timeout), daemon=True)
        thread.start()
        
    def _send_command_thread(self, command, timeout):
        """Background thread to send command and receive response"""
        # Reconnect for each command (server closes connection after each response)
        host = self.host_var.get()
        port = int(self.port_var.get())
        
        temp_sock = None
        try:
            # Create new connection for this command
            self._log(f"Connecting to {host}:{port}...")
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_sock.settimeout(timeout + 5.0)
            temp_sock.connect((host, port))
            self._log("Connected")
            
            # Prepare command JSON
            cmd_data = {
                "command": command,
                "timeout": timeout
            }
            
            # Send command
            message = json.dumps(cmd_data) + '\n'
            temp_sock.sendall(message.encode('utf-8'))
            self._log("Command sent, waiting for response...")
            
            # Receive response
            data = b''
            while True:
                chunk = temp_sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break
            
            if not data:
                self._log("✗ Server closed connection without response")
                self._log("=" * 60)
                self.root.after(0, lambda: self.send_button.config(state='normal'))
                return
            
            # Parse response
            response = json.loads(data.decode('utf-8'))
            
            # Display response (pretty printed JSON)
            self._log("\nResponse received:")
            self._log(json.dumps(response, indent=2))
            
            # Summary
            self._log("-" * 60)
            if response.get('success'):
                self._log(f"✓ Command successful (took {response.get('execution_time', 0):.2f}s)")
                
                if response.get('warnings'):
                    self._log(f"⚠ Warnings: {len(response['warnings'])}")
                    
            else:
                self._log(f"✗ Command failed")
                if response.get('error'):
                    self._log(f"Error: {response['error']}")
                elif response.get('errors'):
                    self._log(f"Errors: {response['errors']}")
            
            self._log("=" * 60)
            
            # Re-enable send button
            self.root.after(0, lambda: self.send_button.config(state='normal'))
            
        except socket.timeout:
            self._log(f"✗ Timeout waiting for response (>{timeout}s)")
            self._log("=" * 60)
            self.root.after(0, lambda: self.send_button.config(state='normal'))
            
        except ConnectionRefusedError:
            self._log(f"✗ Connection refused - server not running")
            self._log("=" * 60)
            self.root.after(0, lambda: self.send_button.config(state='normal'))
            
        except Exception as e:
            self._log(f"✗ Error: {e}")
            self._log("=" * 60)
            self.root.after(0, lambda: self.send_button.config(state='normal'))
        
        finally:
            # Always close the temporary socket
            if temp_sock:
                try:
                    temp_sock.close()
                except:
                    pass
    
    def _on_history_select(self, event):
        """When history item is selected, populate command entry"""
        selection = self.history_listbox.curselection()
        if selection:
            command = self.history_listbox.get(selection[0])
            self.command_var.set(command)
    
    def on_closing(self):
        """Handle window close"""
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CAPClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
