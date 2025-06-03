"""Tailscale API client."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import keyring
from authlib.integrations.httpx_client import OAuth2Client
from pydantic import BaseModel


class Device(BaseModel):
    """Tailscale device model."""

    id: str
    name: str
    ip: str
    last_seen: str
    os: str
    tags: Optional[List[str]] = None


class ApiKey(BaseModel):
    """Tailscale API key model."""

    id: str
    name: str
    created: str
    expires: str
    capabilities: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class TailscaleAPI:
    """Tailscale API client."""

    API_BASE_URL = "https://api.tailscale.com/api/v2"
    AUTH_SERVICE_NAME = "tailnet-admin"

    def __init__(self, tailnet: str, token: Optional[str] = None):
        """Initialize Tailscale API client.

        Args:
            tailnet: Tailnet name (e.g., example.com)
            token: API access token (optional)
        """
        self.tailnet = tailnet
        self.token = token

        # Configure client with timeouts, retries and headers
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(10.0, connect=5.0)

        # Create a transport with automatic retries
        transport = httpx.HTTPTransport(retries=3)

        self.client = httpx.Client(
            base_url=self.API_BASE_URL,
            timeout=timeout,
            limits=limits,
            transport=transport,
            headers={
                "User-Agent": f"tailnet-admin/{__import__('tailnet_admin').__version__}",
                "Accept": "application/json",
            },
        )

        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @classmethod
    def from_stored_auth(cls) -> "TailscaleAPI":
        """Create API client from stored authentication.

        Returns:
            TailscaleAPI: Authenticated API client

        Raises:
            ValueError: If no stored authentication found or token is expired
        """
        import time

        config_dir = Path.home() / ".config" / "tailnet-admin"
        config_file = config_dir / "config.json"

        if not config_file.exists():
            raise ValueError(
                "No stored authentication found. Run 'tailnet-admin auth' first."
            )

        with open(config_file, "r") as f:
            config = json.load(f)

        tailnet = config.get("tailnet")
        if not tailnet:
            raise ValueError("Invalid config file. Run 'tailnet-admin auth' again.")

        token = keyring.get_password(cls.AUTH_SERVICE_NAME, tailnet)
        if not token:
            raise ValueError("No stored token found. Run 'tailnet-admin auth' again.")

        # Check if token is expired
        if "expires_at" in config:
            expires_at = config.get("expires_at", 0)
            now = time.time()

            if expires_at < now:
                # Token has expired
                time_expired = int((now - expires_at) / 60)  # minutes
                raise ValueError(
                    f"Your OAuth token expired {time_expired} minutes ago. "
                    f"This is why you're getting 403 errors on write operations. "
                    f"Please run 'tailnet-admin auth' to get a new token."
                )

            # If token expires soon, warn about it
            minutes_left = int((expires_at - now) / 60)
            if minutes_left < 5:  # Less than 5 minutes left
                logging.warning(
                    f"Warning: Your token will expire in {minutes_left} minutes. "
                    f"Consider running 'tailnet-admin auth' soon to refresh it."
                )

        return cls(tailnet=tailnet, token=token)

    def authenticate(self, client_id: str, client_secret: str) -> None:
        """Authenticate with Tailscale API using OAuth client credentials flow.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Raises:
            ValueError: If authentication fails
        """
        import time

        from rich.console import Console

        console = Console()

        try:
            # Using OAuth 2.0 client credentials grant type
            # as per https://tailscale.com/kb/1215/oauth-clients#tailscale-oauth-token-endpoint
            token_endpoint = "https://api.tailscale.com/api/v2/oauth/token"

            # Prepare the request data for client credentials grant
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            console.print("Authenticating with Tailscale API...")
            response = httpx.post(token_endpoint, data=data, headers=headers)
            response.raise_for_status()

            token_info = response.json()
            token = token_info.get("access_token")
            scope = token_info.get("scope", "unknown")

            if not token:
                raise ValueError("No access token received")

            # Log the granted scopes to help troubleshoot permission issues
            logging.info(f"OAuth token received with scopes: {scope}")

            # Store token and tailnet info securely
            config_dir = Path.home() / ".config" / "tailnet-admin"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Tokens expire after 1 hour (3600 seconds) as per Tailscale docs
            expires_in = token_info.get("expires_in", 3600)
            expires_at = time.time() + expires_in

            with open(config_dir / "config.json", "w") as f:
                json.dump(
                    {
                        "tailnet": self.tailnet,
                        "token_type": token_info.get("token_type", "Bearer"),
                        "expires_at": expires_at,
                    },
                    f,
                )

            # Store only the access token in the keyring
            keyring.set_password(self.AUTH_SERVICE_NAME, self.tailnet, token)

            # Update current instance
            self.token = token
            self.client.headers.update({"Authorization": f"Bearer {token}"})

            # Verify the token has the necessary permissions by testing a write operation
            # This helps catch permission issues early
            try:
                # First get a device to test with
                devices_response = self.client.get(f"/tailnet/{self.tailnet}/devices")
                devices_response.raise_for_status()
                devices = devices_response.json().get("devices", [])

                # If we have devices, test a write operation that won't change anything
                if devices:
                    test_device = devices[0]
                    device_id = test_device.get("id")
                    current_tags = test_device.get("tags", [])

                    # Try to update tags with the same tags (no actual change)
                    try:
                        self.client.post(
                            f"/device/{device_id}/tags",
                            json={"tags": current_tags},
                            timeout=3.0,
                        ).raise_for_status()
                        console.print("[green]✓ Write permissions verified.[/green]")
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 403:
                            console.print(
                                "\n[yellow]⚠️ Warning: Your token doesn't have write permissions![/yellow]"
                            )
                            console.print(
                                "Even though authentication succeeded, you won't be able to modify devices."
                            )
                            console.print(
                                "This might be due to insufficient scopes granted to your OAuth token."
                            )
                            console.print(
                                "Try requesting 'devices:write' scope explicitly when creating the OAuth client."
                            )
                        else:
                            console.print(
                                f"\n[yellow]⚠️ Warning: Failed to verify write permissions: {e.response.status_code}[/yellow]"
                            )
                    except Exception as verify_e:
                        console.print(
                            f"\n[yellow]⚠️ Warning: Error verifying write permissions: {str(verify_e)}[/yellow]"
                        )
            except Exception:
                # Don't fail authentication if the permission check fails
                pass

            console.print("[green]Authentication successful![/green]")
            console.print(
                f"Token will expire in {expires_in // 3600} hours, {(expires_in % 3600) // 60} minutes."
            )

            # Show the granted scopes to help troubleshoot permission issues
            if "scope" in token_info:
                granted_scopes = token_info.get("scope", "unknown")
                console.print(f"\nGranted scopes: [bold]{granted_scopes}[/bold]")

            else:
                console.print(
                    "\n[yellow]⚠️ Warning: No scope information in token response.[/yellow]"
                )
                console.print("Cannot verify if all required permissions are granted.")
                console.print(
                    "If you encounter 403 errors, you may need to create a new OAuth client."
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Authentication failed: Invalid client ID or secret")
            elif e.response.status_code == 400:
                error_msg = "Authentication failed: Invalid request"
                try:
                    error_data = e.response.json()
                    if "error_description" in error_data:
                        error_msg = (
                            f"Authentication failed: {error_data['error_description']}"
                        )
                    elif "error" in error_data:
                        error_msg = f"Authentication failed: {error_data['error']}"
                except Exception:
                    pass
                raise ValueError(error_msg)
            else:
                raise ValueError(
                    f"Authentication failed: HTTP {e.response.status_code}"
                )
        except Exception as e:
            raise ValueError(f"Authentication failed: {str(e)}")

    def get_api_key_info(self, key_id: str) -> Dict[str, Any]:
        """Get API key information.

        Args:
            key_id: The API key ID

        Returns:
            Dict[str, Any]: API key information

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        # The Tailscale API documentation indicates the correct endpoint is:
        # GET /api/v2/tailnet/:tailnet/keys/:keyID
        # Note that our client already has the base URL set to https://api.tailscale.com/api/v2
        # So we need to omit the /api/v2 prefix in the endpoint path
        try:
            # This is the correct endpoint according to Tailscale OAuth docs
            response = self.client.get(f"/tailnet/{self.tailnet}/keys/{key_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try alternative endpoint patterns
                try_endpoints = [
                    # Removing '/api/v2' as it's already in the base URL
                    f"/tailnet/{self.tailnet}/key/{key_id}",  # singular 'key'
                    f"/keys/{key_id}",
                    f"/key/{key_id}",
                ]

                for endpoint in try_endpoints:
                    try:
                        alt_response = self.client.get(endpoint)
                        alt_response.raise_for_status()
                        return alt_response.json()
                    except httpx.HTTPStatusError:
                        # Continue to the next endpoint if this one fails
                        continue

                # If we get here, all alternative endpoints failed
                # Raise the original error with more context
                raise ValueError(
                    f"Could not access API key information for key ID '{key_id}'. "
                    f"Tried multiple endpoints but all returned 404 Not Found. "
                    f"Verify that the key ID is correct and belongs to your tailnet."
                ) from e
            elif e.response.status_code == 403:
                raise ValueError(
                    f"Permission denied (403) when accessing API key info. "
                    f"Ensure your OAuth client has the 'keys:read' scope."
                ) from e
            else:
                # For other errors, raise with more context
                raise ValueError(
                    f"Error {e.response.status_code} when accessing API key info: {e.response.text}"
                ) from e

    def get_devices(self) -> List[Device]:
        """Get all devices in the tailnet.

        Returns:
            List[Device]: List of devices
        """
        response = self.client.get(f"/tailnet/{self.tailnet}/devices")
        response.raise_for_status()

        devices_data = response.json().get("devices", [])

        # Process the device data to match our model
        processed_devices = []
        for device_data in devices_data:
            # Extract the main IP address (usually the first one)
            ip = (
                device_data.get("addresses", [""])[0]
                if device_data.get("addresses")
                else ""
            )

            # Create a simplified device object
            device = {
                "id": device_data.get("id", ""),
                "name": device_data.get("hostname", device_data.get("name", "")),
                "ip": ip,
                "last_seen": device_data.get("lastSeen", ""),
                "os": device_data.get("os", ""),
                "tags": device_data.get("tags", []),
            }

            processed_devices.append(Device(**device))

        return processed_devices

    def get_device(self, device_id: str) -> Device:
        """Get details of a specific device.

        Args:
            device_id: The device ID

        Returns:
            Device: The device details

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        response = self.client.get(f"/device/{device_id}")
        response.raise_for_status()

        device_data = response.json()

        # Extract the main IP address (usually the first one)
        ip = (
            device_data.get("addresses", [""])[0]
            if device_data.get("addresses")
            else ""
        )

        # Create a device object
        device = Device(
            id=device_data.get("id", ""),
            name=device_data.get("hostname", device_data.get("name", "")),
            ip=ip,
            last_seen=device_data.get("lastSeen", ""),
            os=device_data.get("os", ""),
            tags=device_data.get("tags", []),
        )

        return device

    def update_device_tags(self, device_id: str, tags: List[str]) -> Device:
        """Update tags for a specific device.

        Args:
            device_id: The device ID
            tags: List of tags to set for the device

        Returns:
            Device: The updated device

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        data = {"tags": tags}

        try:
            response = self.client.post(f"/device/{device_id}/tags", json=data)
            response.raise_for_status()

            # Return the updated device
            return self.get_device(device_id)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # Log more details about the 403 error
                error_details = ""
                try:
                    error_details = e.response.json()
                except:
                    error_details = e.response.text

                raise ValueError(
                    f"Permission denied (403): You don't have write permission to update tags. "
                    f"Check that your OAuth client has the 'devices:write' scope. "
                    f"Details: {error_details}"
                )
            else:
                raise

    def get_keys(self) -> List[ApiKey]:
        """Get all API keys.

        Returns:
            List[ApiKey]: List of API keys
        """
        try:
            response = self.client.get(f"/tailnet/{self.tailnet}/keys")
            response.raise_for_status()

            keys_data = response.json().get("keys", [])

            # Process the key data to match our model
            processed_keys = []
            for key_data in keys_data:
                # Create a key object with all available data
                key = {
                    "id": key_data.get("id", ""),
                    "name": key_data.get("description", key_data.get("name", "")),
                    "created": key_data.get("created", ""),
                    "expires": key_data.get("expires", ""),
                    "capabilities": key_data.get("capabilities", None),
                    "description": key_data.get("description", ""),
                }

                processed_keys.append(ApiKey(**key))

            return processed_keys

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError(
                    f"Permission denied (403) when listing API keys. "
                    f"Ensure your OAuth client has the 'keys:read' scope."
                ) from e
            else:
                # For other errors, raise with more context
                raise ValueError(
                    f"Error {e.response.status_code} when listing API keys: {e.response.text}"
                ) from e
