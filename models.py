"""
Data models and business logic for Equipment Inventory Management System
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

class EquipmentStatus(Enum):
    ACTIVE = "ACTIVE"
    RED_TAGGED = "RED_TAGGED"
    DESTROYED = "DESTROYED"
    IN_FIELD = "IN_FIELD"
    WAREHOUSE = "WAREHOUSE"

class JobStatus(Enum):
    PENDING = "PENDING"
    BID_SUBMITTED = "BID_SUBMITTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class PaymentStatus(Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"

class InspectionResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

@dataclass
class Equipment:
    equipment_id: str
    equipment_type: str
    status: EquipmentStatus
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    first_use_date: Optional[date] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        return self.status == EquipmentStatus.ACTIVE
    
    @property
    def is_red_tagged(self) -> bool:
        return self.status == EquipmentStatus.RED_TAGGED
    
    @property
    def is_destroyed(self) -> bool:
        return self.status == EquipmentStatus.DESTROYED

@dataclass
class EquipmentType:
    type_code: str
    description: str
    is_soft_goods: bool = False
    lifespan_years: Optional[int] = None
    inspection_interval_months: int = 6
    is_active: bool = True
    sort_order: int = 0
    
    @property
    def has_expiration(self) -> bool:
        return self.is_soft_goods and self.lifespan_years is not None

@dataclass
class Inspection:
    inspection_id: int
    equipment_id: str
    inspection_date: date
    result: InspectionResult
    inspector_name: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def passed(self) -> bool:
        return self.result == InspectionResult.PASS
    
    @property
    def failed(self) -> bool:
        return self.result == InspectionResult.FAIL

@dataclass
class StatusChange:
    change_id: int
    equipment_id: str
    old_status: Optional[str]
    new_status: str
    change_date: datetime
    red_tag_date: Optional[date] = None

class BusinessRules:
    """Business rules and validation logic"""
    
    RED_TAG_MAX_DAYS = 30
    DEFAULT_INSPECTION_INTERVAL_MONTHS = 6
    SOFT_GOODS_DEFAULT_LIFESPAN_YEARS = 10
    RECORD_RETENTION_YEARS = 7
    
    @staticmethod
    def validate_equipment_id_format(equipment_id: str) -> bool:
        """Validate equipment ID format: [TYPE]/[001-999]"""
        if not equipment_id or '/' not in equipment_id:
            return False
        
        parts = equipment_id.split('/')
        if len(parts) != 2:
            return False
        
        type_code, number = parts
        if len(type_code) < 1 or len(type_code) > 2:
            return False
        
        try:
            num = int(number)
            return 1 <= num <= 999 and len(number) == 3
        except ValueError:
            return False
    
    @staticmethod
    def calculate_next_inspection_date(last_inspection_date: date, 
                                     interval_months: int = DEFAULT_INSPECTION_INTERVAL_MONTHS) -> date:
        """Calculate next inspection due date"""
        if interval_months <= 0:
            interval_months = BusinessRules.DEFAULT_INSPECTION_INTERVAL_MONTHS
        
        # Add months (approximate using 30 days per month for simplicity)
        return last_inspection_date + timedelta(days=interval_months * 30)
    
    @staticmethod
    def calculate_red_tag_destroy_date(red_tag_date: date) -> date:
        """Calculate date when red tagged equipment must be destroyed"""
        return red_tag_date + timedelta(days=BusinessRules.RED_TAG_MAX_DAYS)
    
    @staticmethod
    def calculate_soft_goods_expiry_date(first_use_date: date, 
                                        lifespan_years: int = SOFT_GOODS_DEFAULT_LIFESPAN_YEARS) -> date:
        """Calculate expiry date for soft goods"""
        if lifespan_years <= 0:
            lifespan_years = BusinessRules.SOFT_GOODS_DEFAULT_LIFESPAN_YEARS
        
        return date(first_use_date.year + lifespan_years, first_use_date.month, first_use_date.day)
    
    @staticmethod
    def is_inspection_overdue(last_inspection_date: Optional[date], 
                            interval_months: int = DEFAULT_INSPECTION_INTERVAL_MONTHS) -> bool:
        """Check if equipment inspection is overdue"""
        if last_inspection_date is None:
            return True
        
        next_due = BusinessRules.calculate_next_inspection_date(last_inspection_date, interval_months)
        return date.today() > next_due
    
    @staticmethod
    def is_soft_goods_expired(first_use_date: Optional[date], 
                            lifespan_years: int = SOFT_GOODS_DEFAULT_LIFESPAN_YEARS) -> bool:
        """Check if soft goods have expired"""
        if first_use_date is None:
            return False
        
        expiry_date = BusinessRules.calculate_soft_goods_expiry_date(first_use_date, lifespan_years)
        return date.today() > expiry_date
    
    @staticmethod
    def get_red_tag_days_remaining(red_tag_date: date) -> int:
        """Get number of days remaining before red tagged equipment must be destroyed"""
        destroy_date = BusinessRules.calculate_red_tag_destroy_date(red_tag_date)
        delta = destroy_date - date.today()
        return max(0, delta.days)
    
    @staticmethod
    def can_return_to_service(current_status: EquipmentStatus) -> bool:
        """Check if equipment can return to active service"""
        # Business rule: Red tagged equipment never returns to service
        return current_status != EquipmentStatus.RED_TAGGED
    
    @staticmethod
    def should_auto_red_tag(inspection_result: InspectionResult) -> bool:
        """Check if equipment should be automatically red tagged"""
        # Business rule: Failed inspections automatically red tag equipment
        return inspection_result == InspectionResult.FAIL

@dataclass
class Job:
    job_id: str
    customer_name: str
    status: JobStatus
    description: Optional[str] = None
    projected_start_date: Optional[date] = None
    projected_end_date: Optional[date] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    job_title: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        return self.status == JobStatus.ACTIVE
    
    @property
    def is_pending(self) -> bool:
        return self.status == JobStatus.PENDING
    
    @property
    def is_completed(self) -> bool:
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        return self.status == JobStatus.CANCELLED
    
    @property
    def can_have_equipment_assigned(self) -> bool:
        """Only ACTIVE jobs can have equipment assigned"""
        return self.is_active
    
    @property
    def location_display(self) -> str:
        """Format location for display"""
        if self.location_city and self.location_state:
            return f"{self.location_city}, {self.location_state}"
        elif self.location_city:
            return self.location_city
        elif self.location_state:
            return self.location_state
        return "Not specified"

@dataclass
class JobBilling:
    billing_id: int
    job_id: str
    payment_status: PaymentStatus
    bid_amount: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    invoice_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_paid(self) -> bool:
        return self.payment_status == PaymentStatus.PAID
    
    @property
    def is_overdue(self) -> bool:
        return self.payment_status == PaymentStatus.OVERDUE
    
    @property
    def bid_amount_display(self) -> str:
        """Format bid amount for display"""
        if self.bid_amount:
            return f"${self.bid_amount:,.2f}"
        return "Not specified"
    
    @property
    def actual_cost_display(self) -> str:
        """Format actual cost for display"""
        if self.actual_cost:
            return f"${self.actual_cost:,.2f}"
        return "Not specified"
