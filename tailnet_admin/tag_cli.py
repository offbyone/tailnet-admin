"""CLI commands for tag management."""

import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table

from tailnet_admin.api import TailscaleAPI
from tailnet_admin.tags import (
    get_all_devices_with_tags,
    rename_tag,
    add_tag_if_has_tag,
    add_tag_if_missing_tag,
    remove_tag_from_all,
    set_device_tags,
    print_tag_changes,
    confirm_changes,
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
                
            table.add_row(
                tag,
                str(len(device_list)),
                devices_str
            )
        
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
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
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
            
        if dry_run:
            console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
            return
            
        # Confirm with the user
        if not yes and not confirm_changes(console):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
            
        # Apply the changes
        rename_tag(api, old_tag, new_tag, dry_run=False)
        console.print(f"[green]Successfully renamed tag on {len(changes)} devices.[/green]")
        
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
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Add a tag to devices that already have another specific tag."""
    try:
        api = TailscaleAPI.from_stored_auth()
        
        # Get the changes that would be made
        changes = add_tag_if_has_tag(api, existing_tag, new_tag, dry_run=True)
        
        console.print(f"[bold]Adding tag[/bold] {new_tag} [bold]to devices with tag[/bold] {existing_tag}")
        print_tag_changes(changes, console)
        
        if not changes:
            return
            
        if dry_run:
            console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
            return
            
        # Confirm with the user
        if not yes and not confirm_changes(console):
            console.print("[yellow]Operation cancelled.[/yellow]")
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
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Add a tag to devices that are missing a specific tag."""
    try:
        api = TailscaleAPI.from_stored_auth()
        
        # Get the changes that would be made
        changes = add_tag_if_missing_tag(api, missing_tag, new_tag, dry_run=True)
        
        console.print(f"[bold]Adding tag[/bold] {new_tag} [bold]to devices without tag[/bold] {missing_tag}")
        print_tag_changes(changes, console)
        
        if not changes:
            return
            
        if dry_run:
            console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
            return
            
        # Confirm with the user
        if not yes and not confirm_changes(console):
            console.print("[yellow]Operation cancelled.[/yellow]")
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
    tag: str = typer.Argument(..., help="Tag to remove from all devices"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Remove a tag from all devices in the tailnet."""
    try:
        api = TailscaleAPI.from_stored_auth()
        
        # Get the changes that would be made
        changes = remove_tag_from_all(api, tag, dry_run=True)
        
        console.print(f"[bold]Removing tag[/bold] {tag} [bold]from all devices[/bold]")
        print_tag_changes(changes, console)
        
        if not changes:
            return
            
        if dry_run:
            console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
            return
            
        # Confirm with the user
        if not yes and not confirm_changes(console):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
            
        # Apply the changes
        remove_tag_from_all(api, tag, dry_run=False)
        console.print(f"[green]Successfully removed tag from {len(changes)} devices.[/green]")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="set")
def set_tags_command(
    device_ids: List[str] = typer.Argument(..., help="Device IDs (comma-separated)"),
    tags: List[str] = typer.Option(..., "--tag", "-t", help="Tags to set (can be used multiple times)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Set specific tags for specific devices (replaces all existing tags)."""
    try:
        api = TailscaleAPI.from_stored_auth()
        
        # Get the changes that would be made
        changes = set_device_tags(api, device_ids, tags, dry_run=True)
        
        tag_list = ", ".join(tags) if tags else "none"
        console.print(f"[bold]Setting tags for {len(device_ids)} devices:[/bold] {tag_list}")
        print_tag_changes(changes, console)
        
        if not changes:
            return
            
        if dry_run:
            console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
            return
            
        # Confirm with the user
        if not yes and not confirm_changes(console):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
            
        # Apply the changes
        set_device_tags(api, device_ids, tags, dry_run=False)
        console.print(f"[green]Successfully updated {len(changes)} devices.[/green]")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command(name="device-tags")
def device_tags_command(
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter devices by name (case-insensitive)"),
    tag_filter: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter devices by tag"),
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
            devices = [d for d in devices if d.tags and tag_filter in d.tags]
        
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
                ", ".join(device.tags) if device.tags else "[dim]none[/dim]"
            )
        
        console.print(table)
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        console.print("[yellow]Try running 'tailnet-admin auth' again.[/yellow]")
        raise typer.Exit(code=1)