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


class ApiKey(BaseModel):
    """Tailscale API key model."""

    id: str
    name: str
    created: str
    expires: str


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
            ValueError: If no stored authentication found
        """
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

            if not token:
                raise ValueError("No access token received")

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

            console.print("[green]Authentication successful![/green]")
            console.print(
                f"Token will expire in {expires_in // 3600} hours, {(expires_in % 3600) // 60} minutes."
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
            }

            processed_devices.append(Device(**device))

        return processed_devices

    def get_keys(self) -> List[ApiKey]:
        """Get all API keys.

        Returns:
            List[ApiKey]: List of API keys
        """
        response = self.client.get(f"/tailnet/{self.tailnet}/keys")
        response.raise_for_status()

        keys_data = response.json().get("keys", [])

        # Process the key data to match our model
        processed_keys = []
        for key_data in keys_data:
            # Create a simplified key object
            key = {
                "id": key_data.get("id", ""),
                "name": key_data.get("description", key_data.get("name", "")),
                "created": key_data.get("created", ""),
                "expires": key_data.get("expires", ""),
            }

            processed_keys.append(ApiKey(**key))

        return processed_keys
