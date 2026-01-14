"""
Test script to check ZKTeco device connection
"""
from zk import ZK
import sys
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
ZK_IP = '192.168.1.130'
ZK_PORT = 4370

print("=" * 60)
print("ZKTeco Connection Test")
print("=" * 60)
print(f"Attempting to connect to: {ZK_IP}:{ZK_PORT}")
print("Please wait...")
print()

zk = ZK(ZK_IP, port=ZK_PORT, timeout=5)

try:
    print("Connecting to device...")
    conn = zk.connect()
    print("✓ SUCCESS! Connected to ZKTeco device")
    print()
    
    # Get device info
    print("Device Information:")
    print(f"  - Firmware Version: {conn.get_firmware_version()}")
    print(f"  - Serial Number: {conn.get_serialnumber()}")
    print(f"  - Platform: {conn.get_platform()}")
    
    # Get user count
    users = conn.get_users()
    print(f"  - Total Users: {len(users)}")
    
    # Get attendance count
    attendances = conn.get_attendance()
    print(f"  - Total Attendance Records: {len(attendances)}")
    
    conn.disconnect()
    print()
    print("✓ Device is working properly!")
    
except Exception as e:
    print(f"✗ FAILED to connect!")
    print(f"Error: {e}")
    print()
    print("Possible reasons:")
    print("  1. Device is turned off")
    print("  2. Wrong IP address")
    print("  3. Device and computer are not on the same network")
    print("  4. Firewall is blocking the connection")
    print()
    print("Solutions:")
    print("  1. Check if device is powered on")
    print("  2. Verify IP address on the device")
    print("  3. Try to ping the device: ping", ZK_IP)
    sys.exit(1)

print("=" * 60)
