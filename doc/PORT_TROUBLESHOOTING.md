# Port Troubleshooting

## Common Port Issues

### Port Already in Use (WinError 10013)

**Error:** `PermissionError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`

**Causes:**
1. Another application is using the port (e.g., another CAP server instance)
2. Windows firewall is blocking the port
3. The port is reserved by Windows

**Solutions:**

#### 1. Try a Different Port
Instead of the default 9000, try:
- 9001, 9002, 9003, etc.
- 8888, 8080 (common alternatives)
- 5000-5999 (often available)

#### 2. Find What's Using the Port
Open Command Prompt as Administrator:
```cmd
netstat -ano | findstr :9000
```
Look at the last column (PID) and find the process:
```cmd
tasklist | findstr <PID>
```

#### 3. Kill the Process (if it's yours)
```cmd
taskkill /F /PID <PID>
```

#### 4. Check Windows Firewall
- Windows Security → Firewall & network protection
- Allow an app through firewall
- Add Python/pythonw.exe if needed

#### 5. Use Ports Above 1024
Ports below 1024 require admin privileges. Always use ports 1024-65535.

## Quick Test

Test if a port is available:
```python
import socket

def test_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        print(f"✓ Port {port} is available")
        return True
    except OSError:
        print(f"✗ Port {port} is NOT available")
        return False

# Test ports
for port in [9000, 9001, 9002, 8888, 5000]:
    test_port(port)
```

## Best Practices

1. **Use high ports**: 9000-9999 or 5000-5999 are usually safe
2. **Document your port**: Keep track of which ports your applications use
3. **Handle errors gracefully**: The GUI apps now show clear error messages
4. **Test before production**: Always test socket code in your environment first
