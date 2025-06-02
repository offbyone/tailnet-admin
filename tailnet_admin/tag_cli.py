"""CLI commands for tag management."""

from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from tailnet_admin.api import TailscaleAPI
from tailnet_admin.tags import (
    add_tag_if_has_tag,
    add_tag_if_missing_tag,
    add_tags_to_devices,
    confirm_changes,
    get_all_devices_with_tags,
    normalize_tag,
    normalize_tags,
    print_tag_changes,
    remove_tag_from_all,
    rename_tag,
    set_device_tags,
)

app = typer.Typer(help="Manage Tailscale device tags")
console = Console()


@app.command(name="list")
def list_tags():
    """List all tags used in the tailnet and the devices using them."""
    try:
        api = TailscaleAPI.from_stored_auth()
        devices = get_all_devices_with_tags(api)

        # Extract all unique tags
        all_tags = set()
        for device in devices:
            if device.tags:
                all_tags.update(device.tags)

        if not all_tags:
            console.print("[yellow]No tags found in this tailnet.[/yellow]")
            return

        # Create a mapping of tags to devices
        tag_to_devices = {}
        for tag in all_tags:
            tag_to_devices[tag] = []

        for device in devices:
            if device.tags:
                for tag in device.tags:
                    if tag in tag_to_devices:
                        tag_to_devices[tag].append(device)

        # Display tags in a table
        table = Table(title="Tags in your tailnet")
        table.add_column("Tag", style="cyan")
        table.add_column("Device Count", style="green")
        table.add_column("Devices", style="dim")

        for tag, device_list in sorted(tag_to_devices.items()):
            devices_str = ", ".join(d.name for d in device_list[:5])
            if len(device_list) > 5:
                devices_str += f" and {len(device_list) - 5} more"

            table.add_row(tag, str(len(device_list)), devices_str)

        console.print(table)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
        raise typer.Exit(code=1)


@app.command(name="rename")
def rename_tag_command(
    old_tag: str = typer.Argument(..., help="Existing tag to rename"),
    new_tag: str = typer.Argument(..., help="New tag name"),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Rename a tag on all devices in the tailnet."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = rename_tag(api, old_tag, new_tag, dry_run=True)

        console.print(f"[bold]Renaming tag:[/bold] {old_tag} → {new_tag}")
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        rename_tag(api, old_tag, new_tag, dry_run=False)
        console.print(
            f"[green]Successfully renamed tag on {len(changes)} devices.[/green]"
        )

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="add-if-has")
def add_if_has_command(
    existing_tag: str = typer.Argument(..., help="Tag that must be present"),
    new_tag: str = typer.Argument(..., help="Tag to add"),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Add a tag to devices that already have another specific tag."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = add_tag_if_has_tag(api, existing_tag, new_tag, dry_run=True)

        console.print(
            f"[bold]Adding tag[/bold] {new_tag} [bold]to devices with tag[/bold] {existing_tag}"
        )
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        add_tag_if_has_tag(api, existing_tag, new_tag, dry_run=False)
        console.print(f"[green]Successfully updated {len(changes)} devices.[/green]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="add-if-missing")
def add_if_missing_command(
    missing_tag: str = typer.Argument(..., help="Tag that must be absent"),
    new_tag: str = typer.Argument(..., help="Tag to add"),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Add a tag to devices that are missing a specific tag."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = add_tag_if_missing_tag(api, missing_tag, new_tag, dry_run=True)

        console.print(
            f"[bold]Adding tag[/bold] {new_tag} [bold]to devices without tag[/bold] {missing_tag}"
        )
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        add_tag_if_missing_tag(api, missing_tag, new_tag, dry_run=False)
        console.print(f"[green]Successfully updated {len(changes)} devices.[/green]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="remove")
def remove_tag_command(
    tag: str = typer.Argument(..., help="Tag to remove"),
    devices: Optional[List[str]] = typer.Option(
        None, "--device", "-d", help="Device name or ID (can be used multiple times)"
    ),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Remove a tag from devices.
    
    If no devices are specified, removes the tag from all devices in the tailnet.
    """
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = remove_tag_from_all(api, tag, device_identifiers=devices, dry_run=True)

        if devices:
            device_str = f"from {len(devices)} specified devices"
        else:
            device_str = "from all devices"
            
        console.print(f"[bold]Removing tag[/bold] {tag} [bold]{device_str}[/bold]")
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        remove_tag_from_all(api, tag, device_identifiers=devices, dry_run=False)
        console.print(
            f"[green]Successfully removed tag from {len(changes)} devices.[/green]"
        )

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="set")
def set_tags_command(
    devices: List[str] = typer.Argument(..., help="Device names or IDs (comma-separated)"),
    tags: List[str] = typer.Option(
        ..., "--tag", "-t", help="Tags to set (can be used multiple times)"
    ),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Set specific tags for specific devices (replaces all existing tags)."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = set_device_tags(api, devices, tags, dry_run=True)

        tag_list = ", ".join(tags) if tags else "none"
        console.print(
            f"[bold]Setting tags for {len(devices)} devices:[/bold] {tag_list}"
        )
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        set_device_tags(api, devices, tags, dry_run=False)
        console.print(f"[green]Successfully updated {len(changes)} devices.[/green]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="add")
def add_tags_command(
    devices: List[str] = typer.Argument(..., help="Device names or IDs (comma-separated)"),
    tags: List[str] = typer.Option(
        ..., "--tag", "-t", help="Tags to add (can be used multiple times)"
    ),
    act: bool = typer.Option(
        False, "--act", "-a", help="Actually apply the changes (default is dry run)"
    ),
):
    """Add tags to specific devices (preserves existing tags)."""
    try:
        api = TailscaleAPI.from_stored_auth()

        # Get the changes that would be made
        changes = add_tags_to_devices(api, devices, tags, dry_run=True)

        tag_list = ", ".join(tags) if tags else "none"
        console.print(
            f"[bold]Adding tags to {len(devices)} devices:[/bold] {tag_list}"
        )
        print_tag_changes(changes, console)

        if not changes:
            return

        if not act:
            console.print(
                "[yellow]Dry run mode. No changes were made. Use --act to apply changes.[/yellow]"
            )
            return

        # Apply the changes
        add_tags_to_devices(api, devices, tags, dry_run=False)
        console.print(f"[green]Successfully updated {len(changes)} devices.[/green]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="device-tags")
def device_tags_command(
    name_filter: Optional[str] = typer.Option(
        None, "--name", "-n", help="Filter devices by name (case-insensitive)"
    ),
    tag_filter: Optional[str] = typer.Option(
        None, "--tag", "-t", help="Filter devices by tag"
    ),
):
    """List all devices with their tags."""
    try:
        api = TailscaleAPI.from_stored_auth()
        devices = get_all_devices_with_tags(api)

        # Apply filters if provided
        if name_filter:
            name_filter = name_filter.lower()
            devices = [d for d in devices if name_filter in d.name.lower()]

        if tag_filter:
            normalized_tag_filter = normalize_tag(tag_filter)
            devices = [d for d in devices if d.tags and normalized_tag_filter in d.tags]

        if not devices:
            console.print("[yellow]No devices found matching the filters.[/yellow]")
            return

        # Display devices in a table
        table = Table(title="Devices and Tags")
        table.add_column("Device Name", style="cyan")
        table.add_column("Device ID", style="dim")
        table.add_column("Tags", style="green")

        for device in devices:
            table.add_row(
                device.name,
                device.id,
                ", ".join(device.tags) if device.tags else "[dim]none[/dim]",
            )

        console.print(table)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
        raise typer.Exit(code=1)
