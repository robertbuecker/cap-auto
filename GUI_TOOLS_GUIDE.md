# CAP Socket GUI Tools - User Guide

## Overview

Two simple Tkinter GUI applications for remote CAP control:
- **cap_server_gui.py**: Starts CAP and listens for commands
- **cap_client_gui.py**: Sends commands to the server

## Architecture

The socket server uses a **one-command-per-connection** model:
1. Client connects
2. Client sends command (JSON)
3. Server executes command
4. Server sends response (JSON)
5. **Server closes connection**

This design is intentional for simplicity and reliability.

## Usage

### Starting the Server

```bash
python cap_server_gui.py
```

**Configuration:**
- **Port**: Default 9005 (use 9005+ or 5000-5999 range)
- **Min CAP Version**: Default 44

**Controls:**
- **START**: Launches CAP and starts socket server
- **STOP**: Stops server and CAP instance

### Using the Client

```bash
python cap_client_gui.py
```

**Configuration:**
- **Host**: Default localhost
- **Port**: Default 9005 (must match server)

**Sending Commands:**
1. Enter CAP command (e.g., `dc proffit`)
2. Set timeout (default 60 seconds)
3. Click **SEND COMMAND** or press Enter
4. View JSON response in display area

**Important:** The client reconnects for each command automatically. No need to manually connect/disconnect.

## Response Format

Commands return JSON with:
```json
{
  "success": true/false,
  "log_output": "full CAP log output",
  "warnings": ["list of warnings"],
  "errors": ["list of errors"],
  "execution_time": 1.23
}
```

## Port Troubleshooting

If you get **WinError 10013** (Permission denied):

1. **Try different ports**: 9005, 9006, 8888, 5000
2. **Check what's using the port**:
   ```cmd
   netstat -ano | findstr :9005
   ```
3. **Run the diagnostic**:
   ```bash
   python test_socket_ports.py
   ```

**Known Issues:**
- Ports 9000-9004 may be blocked on some systems
- Use ports above 9004 or in 5000-5999 range

## Command Examples

**Data Collection:**
```
dc proffit
```

**Get Unit Cell:**
```
gt
```

**Show Image:**
```
sm
```

**Invalid Command:**
```
badcommand
```
Response will have `success: false` and error details.

## Tips

1. **Keep server running**: Start server once, send multiple commands from client
2. **Check logs**: Both GUIs show detailed status messages
3. **Command history**: Client remembers last 10 commands (click to reuse)
4. **Press Enter**: In client, press Enter to send command quickly
5. **Timeout**: Increase for long-running commands (e.g., full data collection)

## Troubleshooting

### "Connection refused"
- Server is not running
- Wrong host/port configuration
- Check server logs for startup errors

### "Server closed connection without response"
- Command took longer than timeout
- CAP crashed or hung
- Check server logs

### "Port already in use"
- Change to different port (both server and client)
- Run `test_socket_ports.py` to find available ports

### Commands not executing
- Check server logs for CAP errors
- Verify CAP is responding (send simple command like `gt`)
- Check timeout is sufficient for command

## Files

- `cap_server_gui.py` - Server application
- `cap_client_gui.py` - Client application  
- `test_socket_ports.py` - Port diagnostic tool
- `PORT_TROUBLESHOOTING.md` - Detailed port help
