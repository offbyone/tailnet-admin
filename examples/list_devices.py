#!/usr/bin/env python3
"""Example script for listing devices in a tailnet."""

from tailnet_admin.api import TailscaleAPI

def main():
    # Create API client - in a real script you would use from_stored_auth()
    # after running the auth command
    api = TailscaleAPI(tailnet="example.com", token="your_token_here")
    
    # Get devices
    devices = api.get_devices()
    
    # Print devices
    for device in devices:
        print(f"{device.name} ({device.id})")
        print(f"  IP: {device.ip}")
        print(f"  Last seen: {device.last_seen}")
        print(f"  OS: {device.os}")
        print("")

if __name__ == "__main__":
    main()