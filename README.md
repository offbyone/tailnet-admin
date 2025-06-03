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

Check OAuth token scopes and permissions:

```bash
tailnet-admin scopes
```

Debug authentication issues:

```bash
tailnet-admin debug-auth
```

List all devices in your tailnet:

```bash
tailnet-admin devices
```

List all API keys:

```bash
tailnet-admin keys

# Show detailed API response
tailnet-admin keys --verbose

# Show raw key IDs for easier copying
tailnet-admin keys --raw-ids
```

Get information about a specific API key:

```bash
tailnet-admin debug-key YOUR_KEY_ID

# Show additional debug information
tailnet-admin debug-key YOUR_KEY_ID --verbose
```

Log out and clear authentication data:

```bash
tailnet-admin logout
```

### Tag Management

tailnet-admin includes powerful tag management capabilities for bulk operations on your Tailscale devices.

List all tags in your tailnet:

```bash
tailnet-admin tag list
```

List all devices with their tags:

```bash
tailnet-admin tag device-tags
```

#### Bulk Tag Operations

Rename a tag on all devices:

```bash
tailnet-admin tag rename old-tag new-tag
```

Add a tag to devices that have another specific tag:

```bash
tailnet-admin tag add-if-has existing-tag new-tag
```

Add a tag to devices that are missing a specific tag:

```bash
tailnet-admin tag add-if-missing missing-tag new-tag
```

Remove a tag from devices (all devices or specific ones):

```bash
# Remove from all devices
tailnet-admin tag remove tag-to-remove

# Remove from specific devices
tailnet-admin tag remove tag-to-remove --device device1 --device laptop2
```

Add tags to specific devices (preserves existing tags):

```bash
tailnet-admin tag add device1,laptop2 --tag tag1 --tag tag2
```

Set specific tags for specific devices (replaces all existing tags):

```bash
tailnet-admin tag set device1,laptop2 --tag tag1 --tag tag2
```

All tag commands support the following options:

- `--act` / `-a`: Actually apply the changes (default is dry run mode)

All commands accept both device names and device IDs for identifying devices. Tags can be specified with or without the `tag:` prefix.

## Creating Tailscale OAuth Clients

To use this tool, you need to create an OAuth client in the Tailscale admin console:

1. Log in to the [Tailscale admin console](https://login.tailscale.com/admin)
2. Navigate to Settings > OAuth clients
3. Click "Create OAuth client"
4. Provide a name for your client (e.g., "tailnet-admin CLI")
5. Select the required scopes:
   - `devices:read` - Access device information
   - `devices:write` - Modify device information (required for tag management)
   - `keys:read` - Access API keys information
   - Or use the `all` scope, but note that you may still need to specify individual scopes during token exchange
6. Click "Create client"
7. Save the generated client ID and client secret securely

The client secret is only shown once when created, so make sure to copy it immediately.

This tool uses the OAuth 2.0 client credentials grant type as described in the [Tailscale OAuth documentation](https://tailscale.com/kb/1215/oauth-clients).

### OAuth Scope Issues

If you encounter 403 Forbidden errors when trying to update device tags, it's likely due to missing the `devices:write` scope in your OAuth token. This can happen even if your OAuth client has the `all` scope in the Tailscale admin console.

To troubleshoot scope issues:

1. Run `tailnet-admin scopes` to check which permissions your current token has
2. If permissions are missing, re-authenticate with `tailnet-admin auth`
3. If that doesn't work, create a new OAuth client with explicit scopes rather than the `all` scope

The OAuth token exchange requires specific scopes to be requested, even if your client has the `all` scope. This is why we explicitly request `devices:read devices:write keys:read tailnet:devices` during authentication.

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

### API Key Endpoints

According to the Tailscale API documentation, the endpoint for getting API key information is:

```
GET /api/v2/tailnet/{tailnet}/keys/{keyID}
```

If you're experiencing issues with API key access, you can use the `debug-key` command to diagnose the problem:

```bash
tailnet-admin debug-key YOUR_KEY_ID --verbose
```

This command will try different endpoint patterns and show detailed information about the requests and responses.

## License

MIT
