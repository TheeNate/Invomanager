"""
Database manager for Equipment Inventory Management System
Handles all SQLite database operations
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_path: str = "equipment_inventory.db"):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        # Always create a new connection for thread safety
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row  # Enable column access by name
        return connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def initialize_database(self):
        """Create all tables and insert initial data"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Create tables
        self._create_tables(cursor)
        
        # Insert default equipment types if they don't exist
        self._insert_default_equipment_types(cursor)
        
        conn.commit()
    
    def _create_tables(self, cursor):
        """Create all required tables"""
        
        # Equipment Types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Equipment_Types (
                type_code VARCHAR(2) PRIMARY KEY,
                description VARCHAR(100) NOT NULL,
                is_soft_goods BOOLEAN NOT NULL DEFAULT 0,
                lifespan_years INTEGER,
                inspection_interval_months INTEGER DEFAULT 6,
                is_active BOOLEAN DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)
        
        # Equipment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Equipment (
                equipment_id VARCHAR(8) PRIMARY KEY,
                equipment_type VARCHAR(2) NOT NULL,
                serial_number VARCHAR(50),
                purchase_date DATE,
                first_use_date DATE,
                status TEXT CHECK(status IN ('ACTIVE', 'RED_TAGGED', 'DESTROYED')) DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_type) REFERENCES Equipment_Types(type_code)
            )
        """)
        
        # Inspections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Inspections (
                inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id VARCHAR(8) NOT NULL,
                inspection_date DATE NOT NULL,
                result TEXT CHECK(result IN ('PASS', 'FAIL')) NOT NULL,
                inspector_name VARCHAR(100) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES Equipment(equipment_id)
            )
        """)
        
        # Status Changes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Status_Changes (
                change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id VARCHAR(8) NOT NULL,
                old_status VARCHAR(20),
                new_status VARCHAR(20) NOT NULL,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                red_tag_date DATE,
                FOREIGN KEY (equipment_id) REFERENCES Equipment(equipment_id)
            )
        """)
    
    def _insert_default_equipment_types(self, cursor):
        """Insert default equipment types if they don't exist"""
        default_types = [
            ('D', 'Descender', False, None, 6, True, 1),
            ('R', 'Rope', True, 10, 6, True, 2),
            ('H', 'Harness', True, 10, 6, True, 3),
            ('B', 'Backup Device', False, None, 6, True, 4)
        ]
        
        for type_data in default_types:
            cursor.execute("""
                INSERT OR IGNORE INTO Equipment_Types 
                (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, is_active, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, type_data)
    
    # Equipment CRUD operations
    def add_equipment(self, equipment_type: str, serial_number: str = None, 
                     purchase_date: date = None, first_use_date: date = None) -> str:
        """Add new equipment and return the generated ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            # Generate next equipment ID
            equipment_id = self._generate_equipment_id(equipment_type)
            
            cursor.execute("""
                INSERT INTO Equipment (equipment_id, equipment_type, serial_number, purchase_date, first_use_date)
                VALUES (?, ?, ?, ?, ?)
            """, (equipment_id, equipment_type, serial_number, purchase_date, first_use_date))
            
            # Record initial status change
            cursor.execute("""
                INSERT INTO Status_Changes (equipment_id, old_status, new_status)
                VALUES (?, NULL, 'ACTIVE')
            """, (equipment_id,))
            
            conn.commit()
            return equipment_id
        finally:
            conn.close()
    
    def _generate_equipment_id(self, equipment_type: str) -> str:
        """Generate next available equipment ID for given type"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT equipment_id FROM Equipment 
                WHERE equipment_type = ? 
                ORDER BY equipment_id DESC LIMIT 1
            """, (equipment_type,))
            
            result = cursor.fetchone()
            if result:
                last_id = result[0]
                # Extract number part and increment
                number_part = int(last_id.split('/')[1])
                next_number = number_part + 1
            else:
                next_number = 1
            
            return f"{equipment_type}/{next_number:03d}"
        finally:
            conn.close()
    
    def get_equipment_list(self, status_filter: str = None, type_filter: str = None) -> List[Dict]:
        """Get list of equipment with optional filters"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT e.*, et.description as type_description
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE 1=1
            """
            params = []
            
            if status_filter:
                query += " AND e.status = ?"
                params.append(status_filter)
            
            if type_filter:
                query += " AND e.equipment_type = ?"
                params.append(type_filter)
            
            query += " ORDER BY e.equipment_type, e.equipment_id"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def delete_equipment(self, equipment_id: str) -> bool:
        """Delete equipment entry (only if no inspections exist)"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            # Check if equipment has inspections
            cursor.execute("SELECT COUNT(*) FROM Inspections WHERE equipment_id = ?", (equipment_id,))
            inspection_count = cursor.fetchone()[0]
            
            if inspection_count > 0:
                return False  # Cannot delete equipment with inspections
            
            # Delete status changes first (foreign key constraint)
            cursor.execute("DELETE FROM Status_Changes WHERE equipment_id = ?", (equipment_id,))
            
            # Delete equipment
            cursor.execute("DELETE FROM Equipment WHERE equipment_id = ?", (equipment_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """Get equipment details by ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.*, et.description as type_description, et.is_soft_goods, et.lifespan_years
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE e.equipment_id = ?
            """, (equipment_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()
    
    def update_equipment_status(self, equipment_id: str, new_status: str) -> bool:
        """Update equipment status and record the change"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute("SELECT status FROM Equipment WHERE equipment_id = ?", (equipment_id,))
        result = cursor.fetchone()
        if not result:
            return False
        
        old_status = result[0]
        if old_status == new_status:
            return True
        
        # Update equipment status
        cursor.execute("""
            UPDATE Equipment SET status = ? WHERE equipment_id = ?
        """, (new_status, equipment_id))
        
        # Record status change
        red_tag_date = date.today() if new_status == 'RED_TAGGED' else None
        cursor.execute("""
            INSERT INTO Status_Changes (equipment_id, old_status, new_status, red_tag_date)
            VALUES (?, ?, ?, ?)
        """, (equipment_id, old_status, new_status, red_tag_date))
        
        conn.commit()
        return True
    
    # Inspection operations
    def add_inspection(self, equipment_id: str, inspection_date: date, result: str, 
                      inspector_name: str, notes: str = None) -> int:
        """Add inspection record and update equipment status if failed"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Inspections (equipment_id, inspection_date, result, inspector_name, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (equipment_id, inspection_date, result, inspector_name, notes))
        
        inspection_id = cursor.lastrowid
        
        # If inspection failed, automatically red tag the equipment
        if result == 'FAIL':
            self.update_equipment_status(equipment_id, 'RED_TAGGED')
        
        conn.commit()
        return inspection_id
    
    def get_equipment_inspections(self, equipment_id: str) -> List[Dict]:
        """Get all inspections for equipment"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM Inspections 
            WHERE equipment_id = ? 
            ORDER BY inspection_date DESC
        """, (equipment_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_last_inspection(self, equipment_id: str) -> Optional[Dict]:
        """Get most recent inspection for equipment"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM Inspections 
            WHERE equipment_id = ? 
            ORDER BY inspection_date DESC LIMIT 1
        """, (equipment_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    # Equipment Types operations
    def get_equipment_types(self, active_only: bool = True) -> List[Dict]:
        """Get equipment types"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM Equipment_Types"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY sort_order, type_code"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def add_equipment_type(self, type_code: str, description: str, is_soft_goods: bool = False,
                          lifespan_years: int = None, inspection_interval_months: int = 6) -> bool:
        """Add new equipment type"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            # Get next sort order
            cursor.execute("SELECT MAX(sort_order) FROM Equipment_Types")
            max_sort = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                INSERT INTO Equipment_Types 
                (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, max_sort + 1))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def update_equipment_type(self, type_code: str, description: str, is_soft_goods: bool = False,
                             lifespan_years: int = None, inspection_interval_months: int = 6) -> bool:
        """Update equipment type"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Equipment_Types 
            SET description = ?, is_soft_goods = ?, lifespan_years = ?, inspection_interval_months = ?
            WHERE type_code = ?
        """, (description, is_soft_goods, lifespan_years, inspection_interval_months, type_code))
        
        conn.commit()
        return cursor.rowcount > 0
    
    def deactivate_equipment_type(self, type_code: str) -> bool:
        """Deactivate equipment type (soft delete)"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Equipment_Types SET is_active = 0 WHERE type_code = ?
        """, (type_code,))
        
        conn.commit()
        return cursor.rowcount > 0
    
    # Reporting queries
    def get_overdue_inspections(self) -> List[Dict]:
        """Get equipment with overdue inspections"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       e.status, i.inspection_date as last_inspection_date,
                       et.inspection_interval_months,
                       DATE(i.inspection_date, '+' || et.inspection_interval_months || ' months') as next_due_date
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                LEFT JOIN (
                    SELECT equipment_id, MAX(inspection_date) as inspection_date
                    FROM Inspections 
                    GROUP BY equipment_id
                ) latest ON e.equipment_id = latest.equipment_id
                LEFT JOIN Inspections i ON latest.equipment_id = i.equipment_id 
                    AND latest.inspection_date = i.inspection_date
                WHERE e.status = 'ACTIVE'
                AND (
                    i.inspection_date IS NULL OR 
                    DATE(i.inspection_date, '+' || et.inspection_interval_months || ' months') < DATE('now')
                )
                ORDER BY i.inspection_date ASC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_red_tagged_equipment(self) -> List[Dict]:
        """Get red tagged equipment with days remaining"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       sc.red_tag_date,
                       DATE(sc.red_tag_date, '+30 days') as destroy_by_date,
                       (JULIANDAY(DATE(sc.red_tag_date, '+30 days')) - JULIANDAY(DATE('now'))) as days_remaining
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                JOIN Status_Changes sc ON e.equipment_id = sc.equipment_id
                WHERE e.status = 'RED_TAGGED'
                AND sc.new_status = 'RED_TAGGED'
                AND sc.red_tag_date IS NOT NULL
                ORDER BY sc.red_tag_date ASC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_expiring_soft_goods(self) -> List[Dict]:
        """Get soft goods approaching 10-year expiration"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       e.first_use_date,
                       DATE(e.first_use_date, '+' || et.lifespan_years || ' years') as expiry_date,
                       (JULIANDAY(DATE(e.first_use_date, '+' || et.lifespan_years || ' years')) - JULIANDAY(DATE('now'))) as days_remaining
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE e.status = 'ACTIVE'
                AND et.is_soft_goods = 1
                AND e.first_use_date IS NOT NULL
                AND et.lifespan_years IS NOT NULL
                AND DATE(e.first_use_date, '+' || et.lifespan_years || ' years') > DATE('now')
                AND DATE(e.first_use_date, '+' || et.lifespan_years || ' years') <= DATE('now', '+1 year')
                ORDER BY expiry_date ASC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def export_to_csv(self, table_name: str, filename: str) -> bool:
        """Export table data to CSV"""
        import csv
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            if table_name == "equipment_summary":
                cursor.execute("""
                    SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                           e.serial_number, e.purchase_date, e.first_use_date, e.status,
                           i.inspection_date as last_inspection_date, i.result as last_inspection_result
                    FROM Equipment e
                    JOIN Equipment_Types et ON e.equipment_type = et.type_code
                    LEFT JOIN (
                        SELECT equipment_id, MAX(inspection_date) as inspection_date
                        FROM Inspections GROUP BY equipment_id
                    ) latest ON e.equipment_id = latest.equipment_id
                    LEFT JOIN Inspections i ON latest.equipment_id = i.equipment_id 
                        AND latest.inspection_date = i.inspection_date
                    ORDER BY e.equipment_type, e.equipment_id
                """)
            else:
                cursor.execute(f"SELECT * FROM {table_name}")
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                writer.writerow([description[0] for description in cursor.description])
                
                # Write data
                writer.writerows(cursor.fetchall())
            
            return True
        except Exception:
            return False
