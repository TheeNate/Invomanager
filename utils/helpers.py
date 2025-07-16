"""
Utility functions and helpers for Equipment Inventory Management System
"""

from datetime import datetime, date
from typing import Any, Optional
import csv
import os

def format_date(date_obj: Optional[date], format_str: str = "%Y-%m-%d") -> str:
    """Format date object to string"""
    if date_obj is None:
        return ""
    return date_obj.strftime(format_str)

def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> Optional[date]:
    """Parse date string to date object"""
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), format_str).date()
    except ValueError:
        return None

def format_datetime(dt_obj: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    if dt_obj is None:
        return ""
    return dt_obj.strftime(format_str)

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with optional suffix"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def days_between(start_date: date, end_date: date) -> int:
    """Calculate number of days between two dates"""
    return (end_date - start_date).days

def get_status_color(status: str) -> str:
    """Get color code for equipment status"""
    colors = {
        'ACTIVE': '#28a745',      # Green
        'RED_TAGGED': '#dc3545',  # Red
        'DESTROYED': '#6c757d'    # Gray
    }
    return colors.get(status, '#000000')

def get_inspection_color(result: str) -> str:
    """Get color code for inspection result"""
    colors = {
        'PASS': '#28a745',   # Green
        'FAIL': '#dc3545'    # Red
    }
    return colors.get(result, '#000000')

def create_backup_filename(base_name: str = "equipment_inventory") -> str:
    """Create backup filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_backup_{timestamp}.db"

def export_csv_safe(data: list, filename: str, headers: list = None) -> bool:
    """Safely export data to CSV file"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if data and headers:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            elif data:
                writer = csv.writer(csvfile)
                writer.writerows(data)
        return True
    except Exception:
        return False

def validate_equipment_type_code(type_code: str) -> bool:
    """Validate equipment type code format"""
    if not type_code:
        return False
    return len(type_code) >= 1 and len(type_code) <= 4 and type_code.isalpha()

def normalize_equipment_type_code(type_code: str) -> str:
    """Normalize equipment type code to uppercase"""
    return type_code.upper().strip() if type_code else ""

def generate_inspection_report_filename(equipment_id: str) -> str:
    """Generate filename for inspection report"""
    safe_id = equipment_id.replace('/', '_')
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"inspection_report_{safe_id}_{timestamp}.txt"

def format_equipment_summary(equipment_data: dict) -> str:
    """Format equipment data for display"""
    summary_lines = [
        f"Equipment ID: {equipment_data.get('equipment_id', 'N/A')}",
        f"Type: {equipment_data.get('type_description', 'N/A')}",
        f"Serial Number: {equipment_data.get('serial_number', 'N/A')}",
        f"Status: {equipment_data.get('status', 'N/A')}",
        f"Purchase Date: {format_date(equipment_data.get('purchase_date'))}",
        f"First Use Date: {format_date(equipment_data.get('first_use_date'))}"
    ]
    return "\n".join(summary_lines)

def get_urgency_level(days_remaining: int) -> str:
    """Get urgency level based on days remaining"""
    if days_remaining < 0:
        return "OVERDUE"
    elif days_remaining <= 7:
        return "CRITICAL"
    elif days_remaining <= 30:
        return "HIGH"
    elif days_remaining <= 90:
        return "MEDIUM"
    else:
        return "LOW"

def get_urgency_color(urgency: str) -> str:
    """Get color code for urgency level"""
    colors = {
        'OVERDUE': '#8B0000',    # Dark Red
        'CRITICAL': '#dc3545',   # Red
        'HIGH': '#fd7e14',       # Orange
        'MEDIUM': '#ffc107',     # Yellow
        'LOW': '#28a745'         # Green
    }
    return colors.get(urgency, '#000000')
