"""
Validation functions for Equipment Inventory Management System
"""

import re
from datetime import date, datetime
from typing import Optional, Tuple, List

class ValidationError(Exception):
    """Custom validation error"""
    pass

class EquipmentValidator:
    """Validator for equipment data"""
    
    EQUIPMENT_ID_PATTERN = re.compile(r'^[A-Z]{1,2}/\d{3}$')
    TYPE_CODE_PATTERN = re.compile(r'^[A-Z]{1,2}$')
    
    @staticmethod
    def validate_equipment_id(equipment_id: str) -> Tuple[bool, str]:
        """Validate equipment ID format"""
        if not equipment_id:
            return False, "Equipment ID is required"
        
        if not EquipmentValidator.EQUIPMENT_ID_PATTERN.match(equipment_id):
            return False, "Equipment ID must be in format [TYPE]/[001-999] (e.g., D/001)"
        
        return True, ""
    
    @staticmethod
    def validate_type_code(type_code: str) -> Tuple[bool, str]:
        """Validate equipment type code"""
        if not type_code:
            return False, "Type code is required"
        
        if not EquipmentValidator.TYPE_CODE_PATTERN.match(type_code):
            return False, "Type code must be 1-2 uppercase letters"
        
        return True, ""
    
    @staticmethod
    def validate_serial_number(serial_number: str) -> Tuple[bool, str]:
        """Validate serial number"""
        if serial_number and len(serial_number.strip()) > 50:
            return False, "Serial number must be 50 characters or less"
        
        return True, ""
    
    @staticmethod
    def validate_date(date_value: Optional[date], field_name: str, 
                     required: bool = False, max_date: Optional[date] = None) -> Tuple[bool, str]:
        """Validate date field"""
        if required and date_value is None:
            return False, f"{field_name} is required"
        
        if date_value is None:
            return True, ""
        
        if date_value > date.today():
            return False, f"{field_name} cannot be in the future"
        
        if max_date and date_value > max_date:
            return False, f"{field_name} cannot be after {max_date}"
        
        return True, ""
    
    @staticmethod
    def validate_equipment_dates(first_use_date: Optional[date]) -> Tuple[bool, str]:
        """Validate equipment date"""
        # No specific date relationship validation needed now that purchase_date is removed
        return True, ""

class InspectionValidator:
    """Validator for inspection data"""
    
    @staticmethod
    def validate_inspection_date(inspection_date: Optional[date]) -> Tuple[bool, str]:
        """Validate inspection date"""
        return EquipmentValidator.validate_date(
            inspection_date, "Inspection date", required=True
        )
    
    @staticmethod
    def validate_inspector_name(inspector_name: str) -> Tuple[bool, str]:
        """Validate inspector name"""
        if not inspector_name or not inspector_name.strip():
            return False, "Inspector name is required"
        
        if len(inspector_name.strip()) > 100:
            return False, "Inspector name must be 100 characters or less"
        
        return True, ""
    
    @staticmethod
    def validate_inspection_result(result: str) -> Tuple[bool, str]:
        """Validate inspection result"""
        valid_results = ['PASS', 'FAIL']
        if result not in valid_results:
            return False, f"Result must be one of: {', '.join(valid_results)}"
        
        return True, ""
    
    @staticmethod
    def validate_notes(notes: str) -> Tuple[bool, str]:
        """Validate inspection notes"""
        if notes and len(notes) > 1000:
            return False, "Notes must be 1000 characters or less"
        
        return True, ""

class EquipmentTypeValidator:
    """Validator for equipment type data"""
    
    @staticmethod
    def validate_description(description: str) -> Tuple[bool, str]:
        """Validate type description"""
        if not description or not description.strip():
            return False, "Description is required"
        
        if len(description.strip()) > 100:
            return False, "Description must be 100 characters or less"
        
        return True, ""
    
    @staticmethod
    def validate_lifespan_years(lifespan_years: Optional[int], 
                               is_soft_goods: bool) -> Tuple[bool, str]:
        """Validate lifespan years"""
        if is_soft_goods and lifespan_years is None:
            return False, "Lifespan years is required for soft goods"
        
        if lifespan_years is not None:
            if lifespan_years <= 0 or lifespan_years > 50:
                return False, "Lifespan years must be between 1 and 50"
        
        return True, ""
    
    @staticmethod
    def validate_inspection_interval(interval_months: int) -> Tuple[bool, str]:
        """Validate inspection interval"""
        if interval_months <= 0 or interval_months > 60:
            return False, "Inspection interval must be between 1 and 60 months"
        
        return True, ""

class FormValidator:
    """Combined form validation"""
    
    @staticmethod
    def validate_equipment_form(equipment_type: str, serial_number: str,
                               first_use_date: Optional[date]) -> List[str]:
        """Validate complete equipment form"""
        errors = []
        
        # Validate type code
        valid, msg = EquipmentValidator.validate_type_code(equipment_type)
        if not valid:
            errors.append(msg)
        
        # Validate serial number
        valid, msg = EquipmentValidator.validate_serial_number(serial_number)
        if not valid:
            errors.append(msg)
        
        # Validate dates
        valid, msg = EquipmentValidator.validate_date(first_use_date, "First use date")
        if not valid:
            errors.append(msg)
        
        # Validate date relationships
        valid, msg = EquipmentValidator.validate_equipment_dates(first_use_date)
        if not valid:
            errors.append(msg)
        
        return errors
    
    @staticmethod
    def validate_inspection_form(equipment_id: str, inspection_date: Optional[date],
                                result: str, inspector_name: str, notes: str) -> List[str]:
        """Validate complete inspection form"""
        errors = []
        
        # Validate equipment ID
        valid, msg = EquipmentValidator.validate_equipment_id(equipment_id)
        if not valid:
            errors.append(msg)
        
        # Validate inspection date
        valid, msg = InspectionValidator.validate_inspection_date(inspection_date)
        if not valid:
            errors.append(msg)
        
        # Validate result
        valid, msg = InspectionValidator.validate_inspection_result(result)
        if not valid:
            errors.append(msg)
        
        # Validate inspector name
        valid, msg = InspectionValidator.validate_inspector_name(inspector_name)
        if not valid:
            errors.append(msg)
        
        # Validate notes
        valid, msg = InspectionValidator.validate_notes(notes)
        if not valid:
            errors.append(msg)
        
        return errors
    
    @staticmethod
    def validate_equipment_type_form(type_code: str, description: str,
                                   is_soft_goods: bool, lifespan_years: Optional[int],
                                   inspection_interval: int) -> List[str]:
        """Validate complete equipment type form"""
        errors = []
        
        # Validate type code
        valid, msg = EquipmentValidator.validate_type_code(type_code)
        if not valid:
            errors.append(msg)
        
        # Validate description
        valid, msg = EquipmentTypeValidator.validate_description(description)
        if not valid:
            errors.append(msg)
        
        # Validate lifespan
        valid, msg = EquipmentTypeValidator.validate_lifespan_years(lifespan_years, is_soft_goods)
        if not valid:
            errors.append(msg)
        
        # Validate inspection interval
        valid, msg = EquipmentTypeValidator.validate_inspection_interval(inspection_interval)
        if not valid:
            errors.append(msg)
        
        return errors
