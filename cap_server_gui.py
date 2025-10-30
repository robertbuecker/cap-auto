"""
CAP Socket Server GUI

Simple Tkinter GUI to start a CAP instance and listen for remote commands.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from cap_auto.cap_control import CAPInstance, CAPListenModeError

class CAPServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAP Socket Server")
        self.root.geometry("600x500")
        
        self.cap = None
        self.server_running = False
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Port configuration frame
        port_frame = ttk.LabelFrame(self.root, text="Server Configuration", padding=10)
        port_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(port_frame, text="Port:").grid(row=0, column=0, sticky='w', padx=5)
        self.port_var = tk.StringVar(value="9005")
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Label(port_frame, text="Min CAP Version:").grid(row=1, column=0, sticky='w', padx=5)
        self.min_version_var = tk.StringVar(value="44")
        ttk.Entry(port_frame, textvariable=self.min_version_var, width=10).grid(row=1, column=1, sticky='w', padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="START", command=self._start_server, width=15)
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="STOP", command=self._stop_server, width=15, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, height=20)
        self.status_text.pack(fill='both', expand=True)
        
        # Make status text read-only
        self.status_text.config(state='disabled')
        
    def _log(self, message):
        """Add message to status text"""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + '\n')
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')
        
    def _start_server(self):
        """Start CAP instance and socket server"""
        try:
            port = int(self.port_var.get())
            if port < 1024 or port > 65535:
                messagebox.showerror("Error", "Port must be between 1024 and 65535")
                return
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        try:
            min_version = int(self.min_version_var.get())
        except ValueError:
            messagebox.showerror("Error", "Min version must be a number")
            return
        
        # Disable controls
        self.start_button.config(state='disabled')
        self.port_entry.config(state='disabled')
        
        self._log("=" * 60)
        self._log("Starting CAP server...")
        
        # Start in background thread
        thread = threading.Thread(target=self._start_server_thread, args=(port, min_version), daemon=True)
        thread.start()
        
    def _start_server_thread(self, port, min_version):
        """Background thread to start CAP and socket server"""
        try:
            # Create CAP instance with custom message callback
            self._log(f"Creating CAP instance (min version: {min_version})...")
            
            self.cap = CAPInstance(
                min_cap_version=min_version,
                start_now=True,
                message_callback=self._log,
                raise_on_error=False  # Don't crash on command errors
            )
            
            self._log(f"CAP started (version {self.cap.cap_version[0]}.{self.cap.cap_version[1]})")
            
            # Start socket server
            self._log(f"Starting socket server on port {port}...")
            actual_port = self.cap.start_socket_server(port=port)
            
            self._log(f"✓ Socket server listening on port {actual_port}")
            self._log("Ready to accept commands from clients")
            self._log("=" * 60)
            
            self.server_running = True
            
            # Enable stop button
            self.root.after(0, lambda: self.stop_button.config(state='normal'))
            
        except PermissionError as e:
            error_msg = f"✗ Port {port} is blocked or already in use\n"
            error_msg += "  Try a different port (e.g., 9001, 9002, 8888)\n"
            error_msg += f"  Windows error: {e}"
            self._log(error_msg)
            self._log("=" * 60)
            self.cap = None
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.port_entry.config(state='normal'))
            self.root.after(0, lambda: messagebox.showerror(
                "Port Error", 
                f"Port {port} is not available.\n\nTry a different port number (e.g., 9001, 9002, 8888)."
            ))
        except Exception as e:
            self._log(f"✗ Error starting server: {e}")
            self._log("=" * 60)
            self.cap = None
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.port_entry.config(state='normal'))
            self.root.after(0, lambda: messagebox.showerror("Server Error", str(e)))
            
    def _stop_server(self):
        """Stop socket server and CAP instance"""
        self._log("=" * 60)
        self._log("Stopping server...")
        
        self.stop_button.config(state='disabled')
        
        # Stop in background thread
        thread = threading.Thread(target=self._stop_server_thread, daemon=True)
        thread.start()
        
    def _stop_server_thread(self):
        """Background thread to stop server"""
        try:
            if self.cap:
                self.cap.stop_socket_server()
                self._log("Socket server stopped")
                
                self.cap.stop(allow_stopped=True)
                self._log("CAP stopped")
                
                self.cap = None
            
            self.server_running = False
            self._log("✓ Server stopped")
            self._log("=" * 60)
            
            # Re-enable start controls
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.port_entry.config(state='normal'))
            
        except Exception as e:
            self._log(f"✗ Error stopping server: {e}")
            self.root.after(0, lambda: self.stop_button.config(state='normal'))
    
    def on_closing(self):
        """Handle window close"""
        if self.server_running:
            if messagebox.askokcancel("Quit", "Server is running. Stop and quit?"):
                if self.cap:
                    try:
                        self.cap.stop_socket_server()
                        self.cap.stop(allow_stopped=True)
                    except:
                        pass
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = CAPServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
