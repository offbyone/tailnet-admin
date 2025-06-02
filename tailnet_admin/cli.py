"""Command-line interface for tailnet-admin."""

import typer
from rich.console import Console
from typing import Optional

from tailnet_admin import __version__
from tailnet_admin.api import TailscaleAPI

app = typer.Typer(help="Tailscale Tailnet administration CLI tool")
console = Console()


@app.callback()
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    """Tailscale Tailnet administration CLI tool."""
    if version:
        console.print(f"tailnet-admin version: {__version__}")
        raise typer.Exit()


@app.command()
def auth(
    client_id: str = typer.Option(..., help="OAuth client ID"),
    client_secret: Optional[str] = typer.Option(None, help="OAuth client secret"),
    tailnet: str = typer.Option(..., help="Tailnet name (e.g., example.com)"),
):
    """Authenticate with Tailscale API using OAuth."""
    try:
        api = TailscaleAPI(tailnet)
        api.authenticate(client_id, client_secret)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try checking your client ID and tailnet name.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def devices():
    """List all devices in the tailnet."""
    try:
        api = TailscaleAPI.from_stored_auth()
        device_list = api.get_devices()
        
        if not device_list:
            console.print("[yellow]No devices found in this tailnet.[/yellow]")
            return
        
        for device in device_list:
            console.print(f"[bold]{device.name}[/bold] ({device.id})")
            console.print(f"  IP: {device.ip}")
            console.print(f"  Last seen: {device.last_seen}")
            console.print(f"  OS: {device.os}")
            console.print("")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def keys():
    """List all API keys."""
    try:
        api = TailscaleAPI.from_stored_auth()
        key_list = api.get_keys()
        
        if not key_list:
            console.print("[yellow]No API keys found in this tailnet.[/yellow]")
            return
        
        for key in key_list:
            console.print(f"[bold]{key.name}[/bold] ({key.id})")
            console.print(f"  Created: {key.created}")
            console.print(f"  Expires: {key.expires}")
            console.print("")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def status():
    """Show authentication status."""
    import json
    from pathlib import Path
    import time
    import keyring
    
    config_dir = Path.home() / ".config" / "tailnet-admin"
    config_file = config_dir / "config.json"
    
    if not config_file.exists():
        console.print("[yellow]Not authenticated.[/yellow]")
        console.print("Run 'tailnet-admin auth' to authenticate with Tailscale API.")
        return
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            
        tailnet = config.get("tailnet", "Unknown")
        
        # Check if token exists in keyring
        token_exists = False
        try:
            token = keyring.get_password(TailscaleAPI.AUTH_SERVICE_NAME, tailnet)
            token_exists = token is not None
        except Exception:
            pass
        
        console.print(f"[bold]Authentication Status[/bold]")
        console.print(f"Tailnet: [green]{tailnet}[/green]")
        
        if token_exists:
            console.print("Token: [green]Present[/green]")
        else:
            console.print("Token: [red]Missing[/red]")
        
        if "expires_at" in config:
            expires_at = config["expires_at"]
            now = time.time()
            
            if expires_at > now:
                expires_in = int(expires_at - now)
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                console.print(f"Token expires in: [green]{hours}h {minutes}m[/green]")
            else:
                console.print("Token: [red]Expired[/red]")
                console.print("Run 'tailnet-admin auth' to authenticate again.")
    except Exception as e:
        console.print(f"[red]Error checking status:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def logout():
    """Clear stored authentication data."""
    import json
    from pathlib import Path
    import keyring
    
    config_dir = Path.home() / ".config" / "tailnet-admin"
    config_file = config_dir / "config.json"
    
    if not config_file.exists():
        console.print("[yellow]No stored authentication found.[/yellow]")
        return
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            
        tailnet = config.get("tailnet")
        if tailnet:
            keyring.delete_password(TailscaleAPI.AUTH_SERVICE_NAME, tailnet)
        
        config_file.unlink()
        
        console.print("[green]Successfully logged out and cleared authentication data.[/green]")
    except Exception as e:
        console.print(f"[red]Error clearing authentication:[/red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()