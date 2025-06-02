"""Command-line interface for tailnet-admin."""

import typer
from rich.console import Console

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
    client_id: str = typer.Option(
        None, help="API client ID", envvar="TAILSCALE_CLIENT_ID"
    ),
    client_secret: str = typer.Option(
        None, help="API client secret", envvar="TAILSCALE_CLIENT_SECRET"
    ),
    tailnet: str = typer.Option(
        None, help="Tailnet name (e.g., example.com)", envvar="TAILSCALE_TAILNET"
    ),
):
    """Authenticate with Tailscale API using client credentials.

    You can provide credentials via command-line options or environment variables:
    - TAILSCALE_CLIENT_ID: API client ID
    - TAILSCALE_CLIENT_SECRET: API client secret
    - TAILSCALE_TAILNET: Tailnet name
    """
    # Check if credentials are provided
    if not client_id:
        console.print("[red]Error:[/red] Client ID is required.")
        console.print(
            "Provide it with --client-id or set the TAILSCALE_CLIENT_ID environment variable."
        )
        raise typer.Exit(code=1)

    if not client_secret:
        console.print("[red]Error:[/red] Client secret is required.")
        console.print(
            "Provide it with --client-secret or set the TAILSCALE_CLIENT_SECRET environment variable."
        )
        raise typer.Exit(code=1)

    if not tailnet:
        console.print("[red]Error:[/red] Tailnet name is required.")
        console.print(
            "Provide it with --tailnet or set the TAILSCALE_TAILNET environment variable."
        )
        raise typer.Exit(code=1)

    try:
        api = TailscaleAPI(tailnet)
        api.authenticate(client_id, client_secret)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print(
            "[yellow]Try checking your client ID, secret, and tailnet name.[/yellow]"
        )
        raise typer.Exit(code=1)


@app.command()
def test_auth():
    """Test the authentication and display basic information."""
    try:
        api = TailscaleAPI.from_stored_auth()
        
        # Make a simple API request to test the token
        response = api.client.get(f"/tailnet/{api.tailnet}")
        response.raise_for_status()
        
        # Extract and display basic information
        data = response.json()
        name = data.get("name", "Unknown")
        console.print(f"[bold]Successfully connected to tailnet:[/bold] [green]{name}[/green]")
        
        # If there's more information available
        if "created" in data:
            console.print(f"Created: {data['created']}")
        if "acls_enforced" in data:
            acls = "Yes" if data["acls_enforced"] else "No"
            console.print(f"ACLs enforced: {acls}")
            
        console.print("\n[green]✓[/green] Authentication is working correctly")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Authentication test failed:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
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
    import time
    from pathlib import Path

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

        console.print(
            "[green]Successfully logged out and cleared authentication data.[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error clearing authentication:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def help():
    """Show detailed help information."""
    console.print("[bold]Tailnet Admin CLI Tool[/bold]")
    console.print("A command-line tool for managing Tailscale tailnets.\n")
    
    console.print("[bold]Authentication[/bold]")
    console.print("Before using this tool, you need to authenticate with Tailscale:")
    console.print("  [green]tailnet-admin auth[/green] --client-id <ID> --client-secret <SECRET> --tailnet <NAME>")
    console.print("\nYou can also use environment variables:")
    console.print("  [green]export TAILSCALE_CLIENT_ID[/green]=your-client-id")
    console.print("  [green]export TAILSCALE_CLIENT_SECRET[/green]=your-client-secret")
    console.print("  [green]export TAILSCALE_TAILNET[/green]=your-tailnet.example.com")
    console.print("  [green]tailnet-admin auth[/green]\n")
    
    console.print("[bold]Available Commands[/bold]")
    console.print("  [green]auth[/green]       Authenticate with the Tailscale API")
    console.print("  [green]status[/green]     Check your authentication status")
    console.print("  [green]test_auth[/green]  Test the API connection")
    console.print("  [green]devices[/green]    List all devices in your tailnet")
    console.print("  [green]keys[/green]       List all API keys")
    console.print("  [green]logout[/green]     Clear authentication data")
    console.print("  [green]help[/green]       Show this help information\n")
    
    console.print("[bold]Creating an OAuth Client[/bold]")
    console.print("To create an OAuth client:")
    console.print("1. Go to [green]https://login.tailscale.com/admin[/green]")
    console.print("2. Navigate to Settings > OAuth clients")
    console.print("3. Click 'Create OAuth client'")
    console.print("4. Select scopes: [green]devices:read keys:read[/green]")
    console.print("5. Save the client ID and secret\n")
    
    console.print("For more information, visit [green]https://tailscale.com/kb/1215/oauth-clients[/green]")


if __name__ == "__main__":
    app()
