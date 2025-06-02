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

Before using the tool, you need to authenticate with the Tailscale API:

```bash
tailnet-admin auth --client-id YOUR_CLIENT_ID --tailnet your-tailnet.example.com
```

You'll need to create an OAuth client in the Tailscale admin console to get a client ID.

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

## API Documentation

This tool uses the Tailscale API. For more information, see the [Tailscale API documentation](https://tailscale.com/api).

## License

MIT