"""Tag management functions for tailnet-admin."""

from typing import Dict, List, Optional, Set, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from tailnet_admin.api import TailscaleAPI, Device


def get_all_devices_with_tags(api: TailscaleAPI) -> List[Device]:
    """Get all devices with their tags.
    
    Args:
        api: TailscaleAPI instance
        
    Returns:
        List[Device]: List of devices with tags
    """
    return api.get_devices()


def find_devices_with_tag(devices: List[Device], tag: str) -> List[Device]:
    """Find devices that have a specific tag.
    
    Args:
        devices: List of devices
        tag: Tag to search for
        
    Returns:
        List[Device]: List of devices with the tag
    """
    return [device for device in devices if device.tags and tag in device.tags]


def find_devices_without_tag(devices: List[Device], tag: str) -> List[Device]:
    """Find devices that don't have a specific tag.
    
    Args:
        devices: List of devices
        tag: Tag to search for absence of
        
    Returns:
        List[Device]: List of devices without the tag
    """
    return [device for device in devices if not device.tags or tag not in device.tags]


def rename_tag(
    api: TailscaleAPI, old_tag: str, new_tag: str, dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Rename a tag on all devices.
    
    Args:
        api: TailscaleAPI instance
        old_tag: Tag to rename
        new_tag: New tag name
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_with_tag(devices, old_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        new_tags = [new_tag if tag == old_tag else tag for tag in old_tags]
        
        if not dry_run:
            api.update_device_tags(device.id, new_tags)
        
        results.append((device, old_tags, new_tags))
    
    return results


def add_tag_if_has_tag(
    api: TailscaleAPI, existing_tag: str, new_tag: str, dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Add a tag to devices that have another specific tag.
    
    Args:
        api: TailscaleAPI instance
        existing_tag: Tag that must be present
        new_tag: Tag to add
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_with_tag(devices, existing_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        
        if new_tag not in old_tags:
            new_tags = old_tags + [new_tag]
            
            if not dry_run:
                api.update_device_tags(device.id, new_tags)
        else:
            # Tag already exists, no change needed
            new_tags = old_tags
        
        results.append((device, old_tags, new_tags))
    
    return results


def add_tag_if_missing_tag(
    api: TailscaleAPI, missing_tag: str, new_tag: str, dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Add a tag to devices that are missing a specific tag.
    
    Args:
        api: TailscaleAPI instance
        missing_tag: Tag that must be absent
        new_tag: Tag to add
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_without_tag(devices, missing_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        
        if new_tag not in old_tags:
            new_tags = old_tags + [new_tag]
            
            if not dry_run:
                api.update_device_tags(device.id, new_tags)
        else:
            # Tag already exists, no change needed
            new_tags = old_tags
        
        results.append((device, old_tags, new_tags))
    
    return results


def remove_tag_from_all(
    api: TailscaleAPI, tag: str, dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Remove a tag from all devices.
    
    Args:
        api: TailscaleAPI instance
        tag: Tag to remove
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_with_tag(devices, tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        new_tags = [t for t in old_tags if t != tag]
        
        if not dry_run:
            api.update_device_tags(device.id, new_tags)
        
        results.append((device, old_tags, new_tags))
    
    return results


def set_device_tags(
    api: TailscaleAPI, device_ids: List[str], tags: List[str], dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Set specific tags for specific devices.
    
    Args:
        api: TailscaleAPI instance
        device_ids: List of device IDs
        tags: List of tags to set
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    results = []
    
    for device_id in device_ids:
        try:
            device = api.get_device(device_id)
            old_tags = device.tags or []
            
            if not dry_run:
                api.update_device_tags(device_id, tags)
            
            results.append((device, old_tags, tags))
        except Exception as e:
            print(f"Error updating device {device_id}: {str(e)}")
    
    return results


def print_tag_changes(changes: List[Tuple[Device, List[str], List[str]]], console: Console):
    """Print tag changes in a table format.
    
    Args:
        changes: List of (device, old_tags, new_tags) tuples
        console: Rich console for output
    """
    if not changes:
        console.print("[yellow]No devices would be affected by this operation.[/yellow]")
        return
    
    table = Table(title="Tag Changes")
    table.add_column("Device Name", style="cyan")
    table.add_column("Device ID", style="dim")
    table.add_column("Old Tags", style="yellow")
    table.add_column("New Tags", style="green")
    
    for device, old_tags, new_tags in changes:
        table.add_row(
            device.name,
            device.id,
            ", ".join(old_tags) if old_tags else "[dim]none[/dim]",
            ", ".join(new_tags) if new_tags else "[dim]none[/dim]"
        )
    
    console.print(table)
    console.print(f"[bold]{len(changes)}[/bold] devices would be affected.")


def confirm_changes(console: Console) -> bool:
    """Ask for confirmation before applying changes.
    
    Args:
        console: Rich console for output
        
    Returns:
        bool: True if user confirmed, False otherwise
    """
    return Confirm.ask("Do you want to apply these changes?")