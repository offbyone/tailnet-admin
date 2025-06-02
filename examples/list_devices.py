#!/usr/bin/env python3
"""Example script for listing devices in a tailnet using environment variables for auth."""

import os
from rich.console import Console
from tailnet_admin.api import TailscaleAPI

def main():
    console = Console()
    
    # Load credentials from environment variables
    client_id = os.environ.get("TAILSCALE_CLIENT_ID")
    client_secret = os.environ.get("TAILSCALE_CLIENT_SECRET")
    tailnet = os.environ.get("TAILSCALE_TAILNET")
    
    if not all([client_id, client_secret, tailnet]):
        console.print("[red]Error:[/red] Missing environment variables")
        console.print("Set TAILSCALE_CLIENT_ID, TAILSCALE_CLIENT_SECRET, and TAILSCALE_TAILNET")
        return 1
    
    try:
        # Create and authenticate API client
        api = TailscaleAPI(tailnet)
        api.authenticate(client_id, client_secret)
        
        # Get devices
        devices = api.get_devices()
        
        # Print devices
        console.print(f"[bold]Devices in {tailnet}:[/bold]")
        console.print("")
        
        for device in devices:
            console.print(f"[bold]{device.name}[/bold] ({device.id})")
            console.print(f"  IP: {device.ip}")
            console.print(f"  Last seen: {device.last_seen}")
            console.print(f"  OS: {device.os}")
            console.print("")
            
        return 0
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())