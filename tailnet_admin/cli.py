"""Command-line interface for tailnet-admin."""

import typer
from rich.console import Console

from tailnet_admin import __version__
from tailnet_admin.api import TailscaleAPI
from tailnet_admin.tag_cli import app as tag_app

app = typer.Typer(help="Tailscale Tailnet administration CLI tool")

# Add tag commands as a subcommand group
app.add_typer(tag_app, name="tag", help="Manage device tags")
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
def keys(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed API response"
    ),
    raw_ids: bool = typer.Option(
        False, "--raw-ids", "-r", help="Show raw key IDs for easier copying"
    ),
):
    """List all API keys."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get raw response first for verbose mode
        response = api.client.get(f"/tailnet/{api.tailnet}/keys")
        response.raise_for_status()
        keys_data = response.json()

        key_list = api.get_keys()

        if not key_list:
            console.print("[yellow]No API keys found in this tailnet.[/yellow]")
            return

        # Print basic info
        console.print(f"[bold]API Keys for Tailnet:[/bold] {api.tailnet}")
        console.print(f"Total keys: {len(key_list)}\n")

        for key in key_list:
            console.print(f"[bold]{key.name}[/bold]")
            if raw_ids:
                console.print(f"  ID: {key.id}")
            else:
                console.print(f"  ID: ({key.id})")
            console.print(f"  Created: {key.created}")
            console.print(f"  Expires: {key.expires}")
            console.print("")

        # If verbose, show the raw API response
        if verbose:
            console.print("\n[bold]Raw API Response:[/bold]")
            console.print(keys_data)

            # Show API endpoint info
            console.print("\n[bold]API Endpoint Information:[/bold]")
            console.print(
                f"List keys URL: {api.client.base_url}/tailnet/{api.tailnet}/keys"
            )
            if key_list:
                example_key = key_list[0].id
                console.print(
                    f"Get single key URL: {api.client.base_url}/tailnet/{api.tailnet}/keys/{example_key}"
                )

            # Show auth header info (partial)
            if api.token:
                console.print(f"Authorization: Bearer {api.token[:10]}...")

            # Show helpful debug command
            console.print("\n[bold]To check a specific key, use:[/bold]")
            if key_list:
                console.print(f"tailnet-admin debug-key {key_list[0].id}")
            else:
                console.print(f"tailnet-admin debug-key KEY_ID")

            # Add reference to Tailscale docs
            console.print("\n[bold]Tailscale API Documentation:[/bold]")
            console.print("The endpoint for getting API key information is:")
            console.print(f"GET /api/v2/tailnet/{{tailnet}}/keys/{{keyID}}")
            console.print("For more information, see https://tailscale.com/api")

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
                if hours > 0:
                    console.print(
                        f"Token expires in: [green]{hours}h {minutes}m[/green]"
                    )
                else:
                    if minutes > 5:
                        console.print(f"Token expires in: [yellow]{minutes}m[/yellow]")
                    else:
                        console.print(
                            f"Token expires in: [red]{minutes}m[/red] (very soon!)"
                        )

                # Check if token has 'devices:write' scope
                try:
                    api = TailscaleAPI.from_stored_auth()
                    console.print("\n[bold]Testing API permissions:[/bold]")
                    # First check read access
                    console.print("- Testing read access (GET devices)... ", end="")
                    api.client.get(f"/tailnet/{tailnet}/devices").raise_for_status()
                    console.print("[green]OK[/green]")

                    # Then check a write operation against the API docs
                    console.print("- Testing write access (POST to API)... ", end="")
                    test_device = api.get_devices()[0] if api.get_devices() else None
                    if test_device:
                        try:
                            # Create a test payload that won't change anything
                            current_tags = test_device.tags or []
                            api.client.post(
                                f"/device/{test_device.id}/tags",
                                json={"tags": current_tags},
                                timeout=3.0,
                            )
                            console.print("[green]OK[/green]")
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 403:
                                console.print("[red]FAILED[/red]")
                                console.print(
                                    "\n[red]⚠️ Your token doesn't have write permissions![/red]"
                                )
                                console.print(
                                    "Make sure your OAuth client has the 'devices:write' scope."
                                )
                                console.print(
                                    "You'll need to create a new OAuth client with the right permissions."
                                )
                            else:
                                console.print(
                                    f"[yellow]ERROR[/yellow] ({e.response.status_code})"
                                )
                    else:
                        console.print("[yellow]SKIPPED[/yellow] (no devices found)")
                except Exception as e:
                    console.print(f"[red]Error testing API:[/red] {str(e)}")
            else:
                time_expired = int((now - expires_at) / 60)  # minutes
                console.print(f"Token: [red]Expired {time_expired} minutes ago[/red]")
                console.print(
                    "[bold yellow]This is why you're getting 403 errors on write operations.[/bold yellow]"
                )
                console.print("Run 'tailnet-admin auth' to authenticate again.")
    except Exception as e:
        console.print(f"[red]Error checking status:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="debug-key")
def debug_key(
    key_id: str = typer.Argument(..., help="API key ID to check"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show additional debug information"
    ),
):
    """Debug API key endpoint access issues."""
    import httpx

    try:
        # Get API client
        api = TailscaleAPI.from_stored_auth()
        tailnet = api.tailnet

        console.print(f"[bold]Testing API key endpoint access for:[/bold] {key_id}")
        console.print(f"Tailnet: {tailnet}")

        # Show API client configuration if verbose
        if verbose:
            console.print("\n[bold]API Client Configuration:[/bold]")
            console.print(f"Base URL: {api.client.base_url}")
            console.print(f"Timeout: {api.client.timeout}")
            # Show token prefix (not the full token for security)
            if api.token:
                console.print(f"Token prefix: {api.token[:10]}...")

            # Show headers (excluding Authorization)
            headers = {
                k: v
                for k, v in api.client.headers.items()
                if k.lower() != "authorization"
            }
            console.print(f"Headers: {headers}")

        # List of endpoints to try
        endpoints = [
            # Standard endpoint from documentation
            # The base URL already includes /api/v2, so we don't include it in the path
            f"/tailnet/{tailnet}/keys/{key_id}",
            # Alternative endpoint patterns to try
            f"/tailnet/{tailnet}/key/{key_id}",
            f"/key/{key_id}",
            f"/keys/{key_id}",
        ]

        # Try each endpoint
        console.print("\n[bold]Testing possible API endpoints:[/bold]")
        console.print(f"Full base URL: {api.client.base_url}")

        for endpoint in endpoints:
            full_url = f"{api.client.base_url}{endpoint}"
            console.print(f"\nTrying: {full_url}")

            try:
                # Make the request with detailed error handling
                response = api.client.get(endpoint)
                response.raise_for_status()

                # Success - print the response
                console.print(f"[green]✓ SUCCESS![/green] Endpoint works: {endpoint}")
                console.print("\n[bold]Response data:[/bold]")
                console.print(response.json())

                # Show how to use this endpoint in your code
                console.print("\n[bold]To use this endpoint in your code:[/bold]")
                console.print(f'api.client.get("{endpoint}")')
                return
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                console.print(f"[red]✗ Error {status}[/red]")

                # Try to get error details
                try:
                    error_details = e.response.json()
                    console.print(f"  Error details: {error_details}")
                except:
                    console.print(f"  Error text: {e.response.text[:100]}")

        # No success with any endpoint
        console.print("\n[red]All endpoints failed.[/red]")

        # Try using the high-level API method
        console.print("\n[bold]Trying high-level API method:[/bold]")
        try:
            result = api.get_api_key_info(key_id)
            console.print(
                "[green]✓ SUCCESS![/green] Using api.get_api_key_info() worked!"
            )
            console.print("\n[bold]Response data:[/bold]")
            console.print(result)
        except Exception as e:
            console.print(f"[red]✗ Failed:[/red] {str(e)}")

            console.print("\n[bold]Troubleshooting tips:[/bold]")
            console.print("1. Check if the key ID is correct")
            console.print("2. Verify that your OAuth token has the 'keys:read' scope")
            console.print("3. Make sure the key belongs to your tailnet")
            console.print(
                "4. Try listing all keys with 'tailnet-admin keys --verbose' first"
            )
            console.print(
                "5. The API key ID might be different from what's shown in the web UI"
            )
            console.print(
                "6. Check if you need to use 'tskey-' prefix with your key ID"
            )

            # Recommend running 'keys' command
            console.print(
                "\n[bold]Next step:[/bold] Run 'tailnet-admin keys --verbose' to see all available keys"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="scopes")
def scopes():
    """Show OAuth token scopes and permissions."""
    import json
    import time
    from pathlib import Path
    
    import httpx
    import keyring
    
    config_dir = Path.home() / ".config" / "tailnet-admin"
    config_file = config_dir / "config.json"
    
    console.print("[bold]OAuth Token Scopes[/bold]\n")
    
    if not config_file.exists():
        console.print("[red]Not authenticated.[/red]")
        console.print("Run 'tailnet-admin auth' to authenticate with Tailscale API.")
        return
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        
        tailnet = config.get("tailnet")
        token = keyring.get_password(TailscaleAPI.AUTH_SERVICE_NAME, tailnet)
        
        if not token:
            console.print("[red]No token found.[/red]")
            console.print("Run 'tailnet-admin auth' to authenticate with Tailscale API.")
            return
        
        # Check if token is expired
        if "expires_at" in config:
            expires_at = config.get("expires_at", 0)
            now = time.time()
            
            if expires_at < now:
                time_expired = int((now - expires_at) / 60)  # minutes
                console.print(f"[red]Token expired {time_expired} minutes ago[/red]")
                console.print("Run 'tailnet-admin auth' to get a new token.")
                return
        
        console.print(f"Tailnet: [green]{tailnet}[/green]")
        
        # Check introspection endpoint if available
        console.print("\n[bold]Checking token permissions...[/bold]")
        
        # Create API client
        api = TailscaleAPI(tailnet=tailnet, token=token)
        
        # Test permissions for key operations
        console.print("\n[bold]Testing permission for key operations:[/bold]")
        try:
            api.client.get(f"/tailnet/{tailnet}/keys").raise_for_status()
            console.print("[green]✓[/green] keys:read - Can list API keys")
        except Exception:
            console.print("[red]✗[/red] keys:read - Cannot list API keys")
        
        # Test permissions for device operations
        console.print("\n[bold]Testing permission for device operations:[/bold]")
        try:
            response = api.client.get(f"/tailnet/{tailnet}/devices")
            response.raise_for_status()
            console.print("[green]✓[/green] devices:read - Can list devices")
            
            # If we have devices, test a write operation
            devices = response.json().get("devices", [])
            if devices:
                test_device = devices[0]
                device_id = test_device.get("id")
                current_tags = test_device.get("tags", [])
                
                try:
                    api.client.post(
                        f"/device/{device_id}/tags",
                        json={"tags": current_tags},
                        timeout=3.0
                    ).raise_for_status()
                    console.print("[green]✓[/green] devices:write - Can modify devices")
                except Exception:
                    console.print("[red]✗[/red] devices:write - Cannot modify devices")
            else:
                console.print("[yellow]?[/yellow] devices:write - No devices to test with")
        except Exception:
            console.print("[red]✗[/red] devices:read - Cannot list devices")
            console.print("[red]✗[/red] devices:write - Cannot modify devices (read failed)")
        
        # Summary and recommendations
        console.print("\n[bold]Summary:[/bold]")
        console.print("If any permissions are missing, you need to:")
        console.print("1. Create a new OAuth client with the required scopes")
        console.print("2. Run 'tailnet-admin auth' with the new client credentials")
        console.print("\nRequired scopes for full functionality:")
        console.print("- devices:read - For listing devices")
        console.print("- devices:write - For modifying device tags")
        console.print("- keys:read - For listing API keys")
        
    except Exception as e:
        console.print(f"[red]Error checking scopes:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="debug-auth")
def debug_auth():
    """Debug authentication issues in detail."""
    import json
    import time
    from pathlib import Path

    import httpx
    import keyring

    config_dir = Path.home() / ".config" / "tailnet-admin"
    config_file = config_dir / "config.json"

    console.print("[bold]Authentication Debugging[/bold]\n")

    # Check config file
    console.print("Checking for config file...")
    if not config_file.exists():
        console.print("[red]❌ No config file found.[/red]")
        console.print("Run 'tailnet-admin auth' to authenticate with Tailscale API.")
        return

    console.print("[green]✓[/green] Config file exists")

    # Check config content
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            console.print("[green]✓[/green] Config file is valid JSON")

        # Check tailnet
        tailnet = config.get("tailnet")
        if not tailnet:
            console.print("[red]❌ Tailnet name missing in config file.[/red]")
            return

        console.print(f"[green]✓[/green] Tailnet name found: {tailnet}")

        # Check expiration
        if "expires_at" in config:
            expires_at = config["expires_at"]
            now = time.time()

            if expires_at > now:
                expires_in = int(expires_at - now)
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                seconds = expires_in % 60

                if hours > 0:
                    console.print(
                        f"[green]✓[/green] Token expiration: {hours}h {minutes}m {seconds}s remaining"
                    )
                elif minutes > 5:
                    console.print(
                        f"[yellow]⚠️[/yellow] Token expiration: {minutes}m {seconds}s remaining (expiring soon)"
                    )
                else:
                    console.print(
                        f"[red]⚠️[/red] Token expiration: {minutes}m {seconds}s remaining (very soon!)"
                    )
            else:
                time_expired = int((now - expires_at) / 60)  # minutes
                console.print(f"[red]❌ Token expired {time_expired} minutes ago[/red]")
                console.print(
                    "[bold yellow]This is why you're getting 403 errors on write operations.[/bold yellow]"
                )
                console.print("Run 'tailnet-admin auth' to authenticate again.")
                return
        else:
            console.print("[yellow]⚠️[/yellow] No expiration time found in config")

        # Check token in keyring
        console.print("\nChecking token in keyring...")
        token = keyring.get_password(TailscaleAPI.AUTH_SERVICE_NAME, tailnet)
        if not token:
            console.print("[red]❌ No token found in keyring.[/red]")
            return

        console.print(f"[green]✓[/green] Token found in keyring")
        console.print(f"[dim]Token prefix: {token[:10]}...[/dim]")

        # Test token with API
        console.print("\n[bold]Testing API permissions:[/bold]")

        # Create API client
        api = TailscaleAPI(tailnet=tailnet, token=token)

        # Test device list (read permission)
        console.print("Testing read access (GET devices)...")
        try:
            response = api.client.get(f"/tailnet/{tailnet}/devices")
            response.raise_for_status()
            devices = response.json().get("devices", [])
            console.print(
                f"[green]✓[/green] Read access successful ({len(devices)} devices found)"
            )

            # Test tag update (write permission)
            if devices:
                console.print("\nTesting write access (POST device tags)...")
                test_device = devices[0]
                device_id = test_device.get("id")
                current_tags = test_device.get("tags", [])

                console.print(f"Test device: {test_device.get('hostname', device_id)}")
                console.print(f"Current tags: {current_tags}")

                try:
                    # Make a request that won't change anything
                    write_response = api.client.post(
                        f"/device/{device_id}/tags",
                        json={"tags": current_tags},
                        timeout=3.0,
                    )
                    write_response.raise_for_status()
                    console.print("[green]✓[/green] Write access successful")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        console.print(
                            "[red]❌ Write access failed with 403 Forbidden[/red]"
                        )
                        console.print("\n[bold red]Root cause found:[/bold red]")
                        console.print(
                            "Your OAuth token doesn't have the 'devices:write' scope."
                        )
                        console.print(
                            "Even though your OAuth client might have the 'all' scope in the Tailscale admin console,"
                        )
                        console.print(
                            "specific scopes must also be requested during the token exchange."
                        )
                        
                        # Try to get response details
                        try:
                            error_details = e.response.json()
                            if 'message' in error_details:
                                console.print(f"\nError message: {error_details['message']}")
                        except:
                            pass
                            
                        console.print("\n[bold]Solution:[/bold]")
                        console.print(
                            "1. Run 'tailnet-admin auth' again with your client credentials"
                        )
                        console.print(
                            "2. If that doesn't work, create a new OAuth client in the Tailscale admin console"
                        )
                        console.print(
                            "3. Make sure to explicitly include the 'devices:write' and 'keys:read' scopes"
                        )
                        console.print(
                            "4. The 'all' scope sometimes doesn't grant proper permissions for token exchange"
                        )
                    else:
                        console.print(
                            f"[red]❌ Write access failed with {e.response.status_code}[/red]"
                        )
                        try:
                            error_details = e.response.json()
                            console.print(f"Error details: {error_details}")
                        except:
                            console.print(f"Error response: {e.response.text}")
            else:
                console.print(
                    "[yellow]⚠️[/yellow] No devices found, skipping write test"
                )

        except httpx.HTTPStatusError as e:
            console.print(
                f"[red]❌ Read access failed with {e.response.status_code}[/red]"
            )
            try:
                error_details = e.response.json()
                console.print(f"Error details: {error_details}")
            except:
                console.print(f"Error response: {e.response.text}")
        except Exception as e:
            console.print(f"[red]❌ API test failed: {str(e)}[/red]")

    except json.JSONDecodeError:
        console.print("[red]❌ Config file is not valid JSON.[/red]")
        return
    except Exception as e:
        console.print(f"[red]❌ Error during debug: {str(e)}[/red]")


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
    console.print(
        "  [green]tailnet-admin auth[/green] --client-id <ID> --client-secret <SECRET> --tailnet <NAME>"
    )
    console.print("\nYou can also use environment variables:")
    console.print("  [green]export TAILSCALE_CLIENT_ID[/green]=your-client-id")
    console.print("  [green]export TAILSCALE_CLIENT_SECRET[/green]=your-client-secret")
    console.print("  [green]export TAILSCALE_TAILNET[/green]=your-tailnet.example.com")
    console.print("  [green]tailnet-admin auth[/green]\n")

    console.print("[bold]Available Commands[/bold]")
    console.print("  [green]auth[/green]       Authenticate with the Tailscale API")
    console.print("  [green]status[/green]     Check your authentication status")
    console.print("  [green]scopes[/green]     Show OAuth token scopes and permissions")
    console.print("  [green]debug-auth[/green] Diagnose authentication problems")
    console.print("  [green]debug-key[/green]  Diagnose API key endpoint issues")
    console.print("  [green]devices[/green]    List all devices in your tailnet")
    console.print("  [green]keys[/green]       List all API keys")
    console.print("  [green]logout[/green]     Clear authentication data")
    console.print("  [green]help[/green]       Show this help information")
    console.print("  [green]tag[/green]        Manage device tags\n")

    console.print("[bold]Tag Management Commands[/bold]")
    console.print("  [green]tag list[/green]             List all tags in your tailnet")
    console.print(
        "  [green]tag device-tags[/green]      List all devices with their tags"
    )
    console.print("  [green]tag rename[/green]           Rename a tag on all devices")
    console.print("  [green]tag add[/green]              Add tags to specific devices")
    console.print(
        "  [green]tag add-if-has[/green]       Add a tag if another tag is present"
    )
    console.print(
        "  [green]tag add-if-missing[/green]   Add a tag if another tag is missing"
    )
    console.print("  [green]tag remove[/green]           Remove a tag from devices")
    console.print(
        "  [green]tag set[/green]              Set specific tags for specific devices"
    )
    console.print(
        "\nAll tag commands support both device names and IDs for device identification."
    )
    console.print("Tags can be specified with or without the 'tag:' prefix.\n")

    console.print("[bold]Creating an OAuth Client[/bold]")
    console.print("To create an OAuth client:")
    console.print("1. Go to [green]https://login.tailscale.com/admin[/green]")
    console.print("2. Navigate to Settings > OAuth clients")
    console.print("3. Click 'Create OAuth client'")
    console.print(
        "4. Select scopes: [green]devices:read devices:write keys:read[/green]"
    )
    console.print("5. Save the client ID and secret\n")

    console.print(
        "For more information, visit [green]https://tailscale.com/kb/1215/oauth-clients[/green]"
    )


if __name__ == "__main__":
    app()
