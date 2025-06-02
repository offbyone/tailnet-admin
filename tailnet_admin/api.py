"""Tailscale API client."""

import json
import httpx
import keyring
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from authlib.integrations.httpx_client import OAuth2Client


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
            token: OAuth access token (optional)
        """
        self.tailnet = tailnet
        self.token = token
        self.client = httpx.Client(base_url=self.API_BASE_URL)
        
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
            raise ValueError("No stored authentication found. Run 'tailnet-admin auth' first.")
            
        with open(config_file, "r") as f:
            config = json.load(f)
            
        tailnet = config.get("tailnet")
        if not tailnet:
            raise ValueError("Invalid config file. Run 'tailnet-admin auth' again.")
        
        token = keyring.get_password(cls.AUTH_SERVICE_NAME, tailnet)
        if not token:
            raise ValueError("No stored token found. Run 'tailnet-admin auth' again.")
            
        return cls(tailnet=tailnet, token=token)
    
    def authenticate(self, client_id: str, client_secret: Optional[str] = None) -> None:
        """Authenticate with Tailscale API using OAuth.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret (optional)
        
        Raises:
            ValueError: If authentication fails
        """
        import webbrowser
        import time
        import secrets
        import http.server
        import socketserver
        import threading
        import urllib.parse
        from rich.console import Console
        
        console = Console()
        
        # Create a secure random state parameter to prevent CSRF
        state = secrets.token_urlsafe(16)
        redirect_uri = "http://localhost:8000/callback"
        
        # Tailscale OAuth endpoints
        auth_endpoint = "https://login.tailscale.com/oauth/authorize"
        token_endpoint = "https://login.tailscale.com/oauth/token"
        
        # Store for the received authorization code
        auth_code = [None]
        auth_completed = threading.Event()
        
        # Handler for the OAuth callback
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.urlparse(self.path).query
                query_params = urllib.parse.parse_qs(query)
                
                if self.path.startswith("/callback"):
                    received_state = query_params.get("state", [""])[0]
                    
                    # Verify state to prevent CSRF attacks
                    if received_state != state:
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"Invalid state parameter. Authentication failed.")
                        return
                    
                    # Get the authorization code
                    auth_code[0] = query_params.get("code", [""])[0]
                    
                    # Send success response
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><head><title>Authentication Successful</title></head>")
                    self.wfile.write(b"<body><h1>Authentication Successful!</h1>")
                    self.wfile.write(b"<p>You can now close this window and return to the terminal.</p>")
                    self.wfile.write(b"</body></html>")
                    
                    # Signal that authentication is complete
                    auth_completed.set()
        
        # Start the local server to receive the callback
        server = socketserver.TCPServer(("localhost", 8000), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        try:
            # Construct the authorization URL
            params = {
                "client_id": client_id,
                "response_type": "code",
                "scope": "devices:read keys:read",
                "redirect_uri": redirect_uri,
                "state": state,
            }
            auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
            
            # Open the browser for the user to authenticate
            console.print(f"Opening browser for authentication...")
            webbrowser.open(auth_url)
            
            # Wait for authentication to complete (timeout after 5 minutes)
            console.print("Waiting for authentication to complete in the browser...")
            auth_completed.wait(300)
            
            if not auth_code[0]:
                raise ValueError("Authentication timed out or was cancelled")
            
            # Exchange the authorization code for an access token
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": auth_code[0],
                "redirect_uri": redirect_uri,
            }
            
            # Remove None values
            token_data = {k: v for k, v in token_data.items() if v is not None}
            
            token_response = httpx.post(token_endpoint, data=token_data)
            token_response.raise_for_status()
            
            token_info = token_response.json()
            token = token_info.get("access_token")
            
            if not token:
                raise ValueError("No access token received")
            
            # Store token and tailnet info securely
            config_dir = Path.home() / ".config" / "tailnet-admin"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(config_dir / "config.json", "w") as f:
                json.dump({
                    "tailnet": self.tailnet,
                    "token_type": token_info.get("token_type", "Bearer"),
                    "expires_at": time.time() + token_info.get("expires_in", 3600),
                }, f)
            
            # Store only the access token in the keyring
            keyring.set_password(self.AUTH_SERVICE_NAME, self.tailnet, token)
            
            # Update current instance
            self.token = token
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            
            console.print("[green]Authentication successful![/green]")
            
        except Exception as e:
            raise ValueError(f"Authentication failed: {str(e)}")
        finally:
            # Shutdown the server
            server.shutdown()
            server.server_close()
    
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
            ip = device_data.get("addresses", [""])[0] if device_data.get("addresses") else ""
            
            # Create a simplified device object
            device = {
                "id": device_data.get("id", ""),
                "name": device_data.get("hostname", device_data.get("name", "")),
                "ip": ip,
                "last_seen": device_data.get("lastSeen", ""),
                "os": device_data.get("os", "")
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
                "expires": key_data.get("expires", "")
            }
            
            processed_keys.append(ApiKey(**key))
            
        return processed_keys