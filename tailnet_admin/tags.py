"""Tag management functions for tailnet-admin."""

from typing import Dict, List, Optional, Set, Tuple, Union
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from tailnet_admin.api import TailscaleAPI, Device


def normalize_tag(tag: str) -> str:
    """Normalize a tag string, adding 'tag:' prefix if not present.
    
    Args:
        tag: The tag string to normalize
        
    Returns:
        str: The normalized tag with 'tag:' prefix if not already present
    """
    if not tag.startswith("tag:"):
        return f"tag:{tag}"
    return tag


def normalize_tags(tags: List[str]) -> List[str]:
    """Normalize a list of tag strings.
    
    Args:
        tags: List of tag strings to normalize
        
    Returns:
        List[str]: List of normalized tags
    """
    return [normalize_tag(tag) for tag in tags]


def resolve_device_identifiers(api: TailscaleAPI, identifiers: List[str]) -> List[str]:
    """Resolve device names or IDs to device IDs.
    
    Args:
        api: TailscaleAPI instance
        identifiers: List of device names or IDs
        
    Returns:
        List[str]: List of device IDs
        
    Raises:
        ValueError: If a device identifier cannot be resolved
    """
    # Get all devices for reference
    all_devices = get_all_devices_with_tags(api)
    
    # Create name to ID mapping
    name_to_id = {device.name.lower(): device.id for device in all_devices}
    id_to_device = {device.id: device for device in all_devices}
    
    # Resolve identifiers
    resolved_ids = []
    unresolved = []
    
    for identifier in identifiers:
        # Check if it's an ID
        if identifier in id_to_device:
            resolved_ids.append(identifier)
            continue
            
        # Check if it's a name (case-insensitive)
        if identifier.lower() in name_to_id:
            resolved_ids.append(name_to_id[identifier.lower()])
            continue
            
        # Not found
        unresolved.append(identifier)
    
    if unresolved:
        raise ValueError(f"Could not resolve device identifiers: {', '.join(unresolved)}")
        
    return resolved_ids


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
        tag: Tag to search for (normalized or not)
        
    Returns:
        List[Device]: List of devices with the tag
    """
    normalized_tag = normalize_tag(tag)
    return [device for device in devices if device.tags and normalized_tag in device.tags]


def find_devices_without_tag(devices: List[Device], tag: str) -> List[Device]:
    """Find devices that don't have a specific tag.
    
    Args:
        devices: List of devices
        tag: Tag to search for absence of (normalized or not)
        
    Returns:
        List[Device]: List of devices without the tag
    """
    normalized_tag = normalize_tag(tag)
    return [device for device in devices if not device.tags or normalized_tag not in device.tags]


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
    # Normalize tags
    normalized_old_tag = normalize_tag(old_tag)
    normalized_new_tag = normalize_tag(new_tag)
    
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_with_tag(devices, normalized_old_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        new_tags = [normalized_new_tag if tag == normalized_old_tag else tag for tag in old_tags]
        
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
    # Normalize tags
    normalized_existing_tag = normalize_tag(existing_tag)
    normalized_new_tag = normalize_tag(new_tag)
    
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_with_tag(devices, normalized_existing_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        
        if normalized_new_tag not in old_tags:
            new_tags = old_tags + [normalized_new_tag]
            
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
    # Normalize tags
    normalized_missing_tag = normalize_tag(missing_tag)
    normalized_new_tag = normalize_tag(new_tag)
    
    devices = get_all_devices_with_tags(api)
    affected_devices = find_devices_without_tag(devices, normalized_missing_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        
        if normalized_new_tag not in old_tags:
            new_tags = old_tags + [normalized_new_tag]
            
            if not dry_run:
                api.update_device_tags(device.id, new_tags)
        else:
            # Tag already exists, no change needed
            new_tags = old_tags
        
        results.append((device, old_tags, new_tags))
    
    return results


def remove_tag_from_all(
    api: TailscaleAPI, tag: str, device_identifiers: Optional[List[str]] = None, dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Remove a tag from all devices or specified devices.
    
    Args:
        api: TailscaleAPI instance
        tag: Tag to remove
        device_identifiers: Optional list of device names or IDs to restrict to
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    # Normalize tag
    normalized_tag = normalize_tag(tag)
    
    # Get all devices
    all_devices = get_all_devices_with_tags(api)
    
    # Filter to specific devices if provided
    if device_identifiers:
        # Resolve device identifiers to IDs
        device_ids = resolve_device_identifiers(api, device_identifiers)
        # Filter devices to only those in the list
        devices = [d for d in all_devices if d.id in device_ids]
    else:
        devices = all_devices
    
    # Find devices that have the tag
    affected_devices = find_devices_with_tag(devices, normalized_tag)
    
    results = []
    
    for device in affected_devices:
        old_tags = device.tags or []
        new_tags = [t for t in old_tags if t != normalized_tag]
        
        if not dry_run:
            api.update_device_tags(device.id, new_tags)
        
        results.append((device, old_tags, new_tags))
    
    return results


def add_tags_to_devices(
    api: TailscaleAPI, device_identifiers: List[str], tags: List[str], dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Add tags to specific devices.
    
    Args:
        api: TailscaleAPI instance
        device_identifiers: List of device names or IDs
        tags: List of tags to add
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    # Resolve device identifiers to IDs
    device_ids = resolve_device_identifiers(api, device_identifiers)
    
    # Normalize tags
    normalized_tags = normalize_tags(tags)
    
    results = []
    
    for device_id in device_ids:
        try:
            device = api.get_device(device_id)
            old_tags = device.tags or []
            
            # Add new tags without duplicates
            new_tags = list(old_tags)
            for tag in normalized_tags:
                if tag not in new_tags:
                    new_tags.append(tag)
            
            if not dry_run:
                api.update_device_tags(device_id, new_tags)
            
            results.append((device, old_tags, new_tags))
        except Exception as e:
            print(f"Error updating device {device_id}: {str(e)}")
    
    return results


def set_device_tags(
    api: TailscaleAPI, device_identifiers: List[str], tags: List[str], dry_run: bool = False
) -> List[Tuple[Device, List[str], List[str]]]:
    """Set specific tags for specific devices (replaces all existing tags).
    
    Args:
        api: TailscaleAPI instance
        device_identifiers: List of device names or IDs
        tags: List of tags to set
        dry_run: If True, don't actually update tags
        
    Returns:
        List[Tuple[Device, List[str], List[str]]]: List of (device, old_tags, new_tags) tuples
    """
    # Resolve device identifiers to IDs
    device_ids = resolve_device_identifiers(api, device_identifiers)
    
    # Normalize tags
    normalized_tags = normalize_tags(tags)
    
    results = []
    
    for device_id in device_ids:
        try:
            device = api.get_device(device_id)
            old_tags = device.tags or []
            
            if not dry_run:
                api.update_device_tags(device_id, normalized_tags)
            
            results.append((device, old_tags, normalized_tags))
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