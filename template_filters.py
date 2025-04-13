"""
Template Filters Module

This module provides Jinja2 template filters for formatting data in templates.
"""

import datetime
from typing import Optional, Union
from flask import Blueprint

# Create blueprint for template filters
template_filters = Blueprint('filters', __name__)

@template_filters.app_template_filter('datetime')
def format_datetime(value: Optional[Union[str, datetime.datetime, float, int]], format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format a datetime object, timestamp, or ISO string for display in templates.
    
    Args:
        value: The datetime value to format (can be datetime object, timestamp, or ISO string)
        format: The format string to use (default: '%Y-%m-%d %H:%M:%S')
        
    Returns:
        Formatted datetime string or empty string if input is None
    """
    if value is None:
        return ''
    
    # Convert input to datetime object
    if isinstance(value, str):
        try:
            # Try to parse as ISO format
            dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try to parse as timestamp
                dt = datetime.datetime.fromtimestamp(float(value))
            except ValueError:
                return value
    elif isinstance(value, (int, float)):
        # Convert timestamp to datetime
        dt = datetime.datetime.fromtimestamp(value)
    elif isinstance(value, datetime.datetime):
        dt = value
    else:
        return str(value)
    
    # Format the datetime
    return dt.strftime(format)

@template_filters.app_template_filter('date')
def format_date(value: Optional[Union[str, datetime.datetime, float, int]], format: str = '%Y-%m-%d') -> str:
    """
    Format a date for display in templates.
    
    Args:
        value: The date value to format
        format: The format string to use (default: '%Y-%m-%d')
        
    Returns:
        Formatted date string
    """
    return format_datetime(value, format)

@template_filters.app_template_filter('time')
def format_time(value: Optional[Union[str, datetime.datetime, float, int]], format: str = '%H:%M:%S') -> str:
    """
    Format a time for display in templates.
    
    Args:
        value: The time value to format
        format: The format string to use (default: '%H:%M:%S')
        
    Returns:
        Formatted time string
    """
    return format_datetime(value, format)

@template_filters.app_template_filter('filesize')
def format_filesize(size: Optional[Union[int, float]]) -> str:
    """
    Format a file size in bytes to a human-readable format.
    
    Args:
        size: The file size in bytes
        
    Returns:
        Human-readable file size string (e.g., "2.5 MB")
    """
    if size is None:
        return ''
    
    # Convert to float for division
    size = float(size)
    
    # Define units and thresholds
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    # Calculate the appropriate unit
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    # Format with appropriate precision
    if unit_index == 0:
        # For bytes, show as integer
        return f"{int(size)} {units[unit_index]}"
    else:
        # For larger units, show with 1 decimal place
        return f"{size:.1f} {units[unit_index]}"

@template_filters.app_template_filter('truncate_middle')
def truncate_middle(text: Optional[str], length: int = 50) -> str:
    """
    Truncate a string in the middle, preserving the start and end.
    
    Args:
        text: The text to truncate
        length: The maximum length of the result
        
    Returns:
        Truncated string with ellipsis in the middle
    """
    if text is None:
        return ''
    
    if len(text) <= length:
        return text
    
    # Calculate how many characters to keep from start and end
    half_length = (length - 3) // 2
    
    # If length is odd, give the extra character to the start
    extra = (length - 3) % 2
    
    return f"{text[:half_length + extra]}...{text[-half_length:]}"

def register_template_filters(app):
    """
    Register all template filters with the Flask app.
    
    Args:
        app: The Flask application instance
    """
    app.register_blueprint(template_filters)