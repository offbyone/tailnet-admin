# tailnet-admin

Tailscale Tailnet administration CLI tool. This tool provides a command-line interface for managing your Tailscale tailnet.

## Installation

```bash
pip install tailnet-admin
```

Or using `uv`:

```bash
uv pip install tailnet-admin
```

## Usage

### Authentication

Before using the tool, you need to authenticate with the Tailscale API. You'll need to create an API client in the Tailscale admin console to get a client ID and client secret.

You can authenticate using command-line options:

```bash
tailnet-admin auth --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET --tailnet your-tailnet.example.com
```

Or using environment variables:

```bash
export TAILSCALE_CLIENT_ID=YOUR_CLIENT_ID
export TAILSCALE_CLIENT_SECRET=YOUR_CLIENT_SECRET
export TAILSCALE_TAILNET=your-tailnet.example.com
tailnet-admin auth
```

You can also mix environment variables and command-line options. Command-line options take precedence over environment variables.

### Commands

Check authentication status:

```bash
tailnet-admin status
```

List all devices in your tailnet:

```bash
tailnet-admin devices
```

List all API keys:

```bash
tailnet-admin keys
```

Log out and clear authentication data:

```bash
tailnet-admin logout
```

## Creating Tailscale API Keys

To use this tool, you need to create an API client in the Tailscale admin console:

1. Log in to the [Tailscale admin console](https://login.tailscale.com/admin)
2. Navigate to Settings > API Access
3. Click "Create API Key"
4. Provide a description (e.g., "tailnet-admin CLI")
5. Select the required permissions:
   - Devices (read)
   - API keys (read)
6. Click "Create"
7. Save the generated client ID and client secret securely

The client ID starts with `tskey-api-` and the client secret is only shown once when created.

## Environment Variables

The following environment variables are supported:

| Variable | Description |
|----------|-------------|
| `TAILSCALE_CLIENT_ID` | Your Tailscale API client ID |
| `TAILSCALE_CLIENT_SECRET` | Your Tailscale API client secret |
| `TAILSCALE_TAILNET` | Your Tailnet name (e.g., example.com) |

You can set these variables in several ways:

1. In your shell session:
   ```bash
   export TAILSCALE_CLIENT_ID=your-client-id
   ```

2. In your shell profile (e.g., `~/.bashrc`, `~/.zshrc`) for persistent configuration.

3. In a `.env` file in the current directory:
   ```
   TAILSCALE_CLIENT_ID=your-client-id
   TAILSCALE_CLIENT_SECRET=your-client-secret
   TAILSCALE_TAILNET=your-tailnet.example.com
   ```
   
   A template `.env.example` file is provided - copy it to `.env` and add your credentials.

## API Documentation

This tool uses the Tailscale API. For more information, see the [Tailscale API documentation](https://tailscale.com/api).

## License

MIT