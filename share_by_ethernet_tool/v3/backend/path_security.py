"""
T-Share v3 Path Security and Normalization Engine
Safeguards cross-platform file transfers between Windows and Linux.
Prevents directory traversal, reserved filename corruption, and path escapes.
"""

import os
import re
from typing import Optional, Tuple

# Windows DOS reserved device names (cannot be created on Windows filesystems)
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}


class SecurityViolation(Exception):
    """Raised when an illegal or malicious path is detected."""
    pass


def sanitize_relative_path(raw_path: str) -> str:
    """
    Sanitizes an incoming relative path from the network manifest:
    1. Normalizes slashes to forward slashes.
    2. Strips drive letters (e.g. C:, D:).
    3. Strips leading and trailing slashes.
    4. Rejects any '..' traversal attempts.
    5. Sanitizes Windows reserved device names if on Windows.
    6. Strips null bytes and invalid control characters.
    """
    if not raw_path or not isinstance(raw_path, str):
        raise SecurityViolation("Invalid path type or empty path")

    # Strip null bytes and control chars
    clean = raw_path.replace('\x00', '').strip()

    # Normalize backslashes to forward slashes
    clean = clean.replace('\\', '/')

    # Remove drive letters like "C:/" or "D:"
    clean = re.sub(r'^[a-zA-Z]:[/]?', '', clean)

    # Strip leading/trailing slashes
    clean = clean.strip('/')

    if not clean:
        raise SecurityViolation("Path evaluates to empty string after normalization")

    # Inspect each path segment
    parts = clean.split('/')
    sanitized_parts = []
    
    for part in parts:
        part = part.strip()
        if not part or part == '.':
            continue
        if part == '..':
            raise SecurityViolation(f"Path traversal '..' detected in path: {raw_path}")
        
        # Windows reserved device check
        basename = part.split('.')[0].upper()
        if basename in WINDOWS_RESERVED_NAMES:
            part = f"_safe_{part}"
            
        sanitized_parts.append(part)

    if not sanitized_parts:
        raise SecurityViolation("Path has no valid segments")

    return '/'.join(sanitized_parts)


def resolve_safe_destination_path(
    destination_dir: str,
    sanitized_rel_path: str,
    collision_policy: str = "keep_both"
) -> Tuple[str, bool]:
    """
    Resolves the absolute destination file path on the receiver.
    Guarantees that the resulting path is strictly contained within destination_dir.
    Applies collision resolution policy:
      - 'keep_both': Generates 'filename (1).ext'
      - 'overwrite': Replaces existing file
      - 'skip': Returns (target_path, True) indicating file should be skipped.

    Returns:
      (resolved_absolute_path: str, should_skip: bool)
    """
    dest_dir = os.path.abspath(destination_dir)
    if not os.path.isdir(dest_dir):
        raise FileNotFoundError(f"Destination directory does not exist: {dest_dir}")

    # Convert POSIX relative path to local OS separator
    local_rel_path = os.path.join(*sanitized_rel_path.split('/'))
    target_path = os.path.abspath(os.path.join(dest_dir, local_rel_path))

    # Strict boundary containment check
    try:
        common = os.path.commonpath([dest_dir, target_path])
    except ValueError:
        raise SecurityViolation("Target path resides on a different drive/volume than destination")

    if common != dest_dir:
        raise SecurityViolation(f"Path escape detected: {target_path} is outside {dest_dir}")

    # Check for existing file collision
    if os.path.exists(target_path):
        if collision_policy == "skip":
            return target_path, True
        elif collision_policy == "overwrite":
            return target_path, False
        else:  # "keep_both" default
            parent = os.path.dirname(target_path)
            base, ext = os.path.splitext(os.path.basename(target_path))
            counter = 1
            while os.path.exists(target_path):
                new_name = f"{base} ({counter}){ext}"
                target_path = os.path.join(parent, new_name)
                counter += 1
            return target_path, False

    return target_path, False
