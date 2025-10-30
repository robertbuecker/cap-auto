"""
Socket Port Diagnostic Tool

Tests if Python can bind to various ports on your system.
Helps diagnose Windows firewall/permission issues.
"""

import socket
import sys

def test_port(port, host='localhost'):
    """Test if we can bind to a specific port"""
    print(f"\nTesting port {port}...", end=' ')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((host, port))
        sock.listen(1)
        actual_port = sock.getsockname()[1]
        sock.close()
        print(f"✓ SUCCESS - Port {actual_port} is available")
        return True
    except PermissionError as e:
        print(f"✗ PERMISSION DENIED")
        print(f"  Error: {e}")
        print(f"  This is likely a Windows firewall issue")
        return False
    except OSError as e:
        print(f"✗ FAILED - {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    print("=" * 70)
    print("Socket Port Diagnostic Tool")
    print("=" * 70)
    
    # Test common ports
    test_ports = [
        9000, 9001, 9002, 9003, 9004, 9005,  # Common CAP ports
        8888, 8080, 8081,                     # Common web dev ports
        5000, 5001, 5555,                     # Common app ports
        12345, 54321                          # Random high ports
    ]
    
    print("\nTesting common ports...")
    success_count = 0
    failed_ports = []
    
    for port in test_ports:
        if test_port(port):
            success_count += 1
        else:
            failed_ports.append(port)
    
    print("\n" + "=" * 70)
    print(f"Results: {success_count}/{len(test_ports)} ports available")
    print("=" * 70)
    
    if success_count == 0:
        print("\n⚠ WARNING: NO PORTS ARE AVAILABLE!")
        print("\nThis indicates a system-level issue. Possible causes:")
        print("  1. Windows Firewall is blocking Python")
        print("  2. Antivirus software is blocking socket operations")
        print("  3. Windows security policy restricts network access")
        print("  4. Python doesn't have network permissions")
        print("\nRecommended actions:")
        print("  1. Run this script as Administrator:")
        print("     Right-click → Run as administrator")
        print("  2. Add Python to Windows Firewall exceptions:")
        print("     Windows Security → Firewall → Allow an app")
        print("  3. Temporarily disable antivirus and test")
        print("  4. Check Windows Event Viewer for security blocks")
        
    elif success_count < len(test_ports) / 2:
        print(f"\n⚠ Some ports failed ({len(failed_ports)} blocked)")
        print(f"Failed ports: {failed_ports}")
        print("\nTry using one of the successful ports instead")
        
    else:
        print("\n✓ Most ports are available - system is working normally")
        print("  If CAP server still fails, the specific port may be in use")
        print("  Use one of the successful ports above")
    
    # Test if we're admin
    print("\n" + "=" * 70)
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            print("Running as: Administrator ✓")
        else:
            print("Running as: Normal user")
            print("  Note: Some ports may require admin privileges")
    except:
        print("Could not determine admin status")
    
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")
