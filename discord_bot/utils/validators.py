"""
Input validation utilities
"""
import re
from datetime import datetime
from typing import Optional


def validate_deadline(deadline_str: str) -> Optional[str]:
    """
    Validate and normalize deadline string
    
    Returns:
        Normalized deadline string or None if invalid
    """
    if not deadline_str or not deadline_str.strip():
        return None
    
    deadline_str = deadline_str.strip()
    
    # Try parsing various formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(deadline_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    return None


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url or not url.strip():
        return True  # Empty URL is valid
    
    url_pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    
    return bool(url_pattern.match(url.strip()))


def validate_priority(priority: str) -> str:
    """
    Validate and normalize priority/colour value
    
    Returns:
        Normalized priority or "default"
    """
    valid_priorities = ["Important", "Moderately Important", "Not Important", "default"]
    
    if not priority or not priority.strip():
        return "default"
    
    priority = priority.strip()
    
    if priority in valid_priorities:
        return priority
    
    # Case-insensitive matching
    for valid in valid_priorities:
        if priority.lower() == valid.lower():
            return valid
    
    return "default"


def validate_status(status: str) -> str:
    """
    Validate and normalize status value
    
    Returns:
        Normalized status or "To Do"
    """
    valid_statuses = ["To Do", "In Progress", "Complete"]
    
    if not status or not status.strip():
        return "To Do"
    
    status = status.strip()
    
    if status in valid_statuses:
        return status
    
    # Case-insensitive matching
    for valid in valid_statuses:
        if status.lower() == valid.lower():
            return valid
    
    return "To Do"
