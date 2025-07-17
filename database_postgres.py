"""
Database manager for Equipment Inventory Management System
Handles PostgreSQL database operations
"""

import psycopg2
import psycopg2.extras
from datetime import date, datetime
from typing import List, Dict, Optional
from decimal import Decimal
import csv
import os

class DatabaseManager:
    def __init__(self, db_url: str = None):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        self.db_url = db_url or os.environ.get('DATABASE_URL')
        if not self.db_url:
            # Fall back to individual PostgreSQL connection parameters
            host = os.environ.get('PGHOST', 'localhost')
            port = os.environ.get('PGPORT', '5432')
            database = os.environ.get('PGDATABASE', 'postgres')
            user = os.environ.get('PGUSER', 'postgres')
            password = os.environ.get('PGPASSWORD', '')

            if host and database and user:
                self.db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                raise ValueError("Database connection parameters not found. Check environment variables.")

    def connect(self):
        """Establish database connection"""
        try:
            # Parse URL to add SSL configuration if needed
            if self.db_url.startswith('postgresql://'):
                # Add SSL mode if not already specified
                if 'sslmode=' not in self.db_url:
                    separator = '&' if '?' in self.db_url else '?'
                    db_url = f"{self.db_url}{separator}sslmode=require"
                else:
                    db_url = self.db_url
            else:
                db_url = self.db_url

            connection = psycopg2.connect(db_url)
            connection.autocommit = False
            return connection
        except psycopg2.OperationalError as e:
            print(f"Database connection failed: {str(e)}")
            print(f"Connection URL (masked): {db_url[:20] if 'db_url' in locals() else self.db_url[:20]}...")
            # Try without SSL as fallback
            try:
                if 'sslmode=' in db_url:
                    fallback_url = db_url.replace('sslmode=require', 'sslmode=prefer')
                    print("Attempting connection with SSL preference instead of requirement...")
                    connection = psycopg2.connect(fallback_url)
                    connection.autocommit = False
                    return connection
            except Exception as fallback_error:
                print(f"Fallback connection also failed: {str(fallback_error)}")
            raise
        except Exception as e:
            print(f"Unexpected database error: {str(e)}")
            raise

    def initialize_database(self):
        """Create all tables and insert initial data"""
        print("Connecting to PostgreSQL database...")
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            print("Creating database tables...")
            self._create_tables(cursor)
            print("Inserting default equipment types...")
            self._insert_default_equipment_types(cursor)

            # Add auth_tokens table
            print("Creating authentication tokens table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            conn.commit()
            print("Database initialization completed successfully!")
        except Exception as e:
            print(f"Database initialization failed: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass  # Connection might already be closed
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass  # Connection might already be closed

    def _create_tables(self, cursor):
        """Create all required tables"""
        # Equipment Types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Equipment_Types (
                type_code VARCHAR(2) PRIMARY KEY,
                description VARCHAR(100) NOT NULL,
                is_soft_goods BOOLEAN DEFAULT FALSE,
                lifespan_years INTEGER,
                inspection_interval_months INTEGER DEFAULT 6,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Jobs (
                job_id VARCHAR(4) PRIMARY KEY,
                customer_name VARCHAR(200) NOT NULL,
                description TEXT,
                projected_start_date DATE,
                projected_end_date DATE,
                location_city VARCHAR(100),
                location_state VARCHAR(50),
                job_title VARCHAR(200),
                status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'BID_SUBMITTED', 'ACTIVE', 'COMPLETED', 'CANCELLED')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Job Billing table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Job_Billing (
                billing_id SERIAL PRIMARY KEY,
                job_id VARCHAR(4) NOT NULL,
                bid_amount DECIMAL(10,2),
                actual_cost DECIMAL(10,2),
                payment_status VARCHAR(20) DEFAULT 'PENDING' CHECK (payment_status IN ('PENDING', 'PAID', 'OVERDUE')),
                invoice_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES Jobs(job_id)
            )
        """)

        # Equipment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Equipment (
                equipment_id VARCHAR(8) PRIMARY KEY,
                equipment_type VARCHAR(2) NOT NULL,
                name VARCHAR(100),
                status VARCHAR(20) DEFAULT 'ACTIVE',
                serial_number VARCHAR(50),
                date_added_to_inventory DATE DEFAULT CURRENT_DATE,
                date_put_in_service DATE,
                job_id VARCHAR(4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_type) REFERENCES Equipment_Types(type_code),
                FOREIGN KEY (job_id) REFERENCES Jobs(job_id)
            )
        """)

        # Add job_id column if it doesn't exist (for existing databases)
        cursor.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='equipment' AND column_name='job_id') THEN
                    ALTER TABLE Equipment ADD COLUMN job_id VARCHAR(4);
                    ALTER TABLE Equipment ADD CONSTRAINT fk_equipment_job 
                    FOREIGN KEY (job_id) REFERENCES Jobs(job_id);
                END IF;
            END $$;
        """)

        # Inspections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Inspections (
                inspection_id SERIAL PRIMARY KEY,
                equipment_id VARCHAR(8) NOT NULL,
                inspection_date DATE NOT NULL,
                result VARCHAR(10) NOT NULL,
                inspector_name VARCHAR(100) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES Equipment(equipment_id)
            )
        """)

        # Status Changes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Status_Changes (
                change_id SERIAL PRIMARY KEY,
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
                INSERT INTO Equipment_Types 
                (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (type_code) DO NOTHING
            """, type_data)

    # Equipment CRUD operations
    def add_equipment(self, equipment_type: str, name: str = None, serial_number: str = None, 
                     date_added_to_inventory: date = None, date_put_in_service: date = None) -> str:
        """Add new equipment and return the generated ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Generate next equipment ID
            equipment_id = self._generate_equipment_id(equipment_type)

            cursor.execute("""
                INSERT INTO Equipment (equipment_id, equipment_type, name, serial_number, date_added_to_inventory, date_put_in_service)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (equipment_id, equipment_type, name, serial_number, date_added_to_inventory, date_put_in_service))

            # Record initial status change
            cursor.execute("""
                INSERT INTO Status_Changes (equipment_id, old_status, new_status)
                VALUES (%s, NULL, 'ACTIVE')
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
                WHERE equipment_type = %s 
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = """
                SELECT e.*, et.description as type_description
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE 1=1
            """
            params = []

            if status_filter:
                query += " AND e.status = %s"
                params.append(status_filter)

            if type_filter:
                query += " AND e.equipment_type = %s"
                params.append(type_filter)

            query += " ORDER BY e.equipment_type, CAST(split_part(e.equipment_id, '/', 2) AS INTEGER)"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_equipment_list_with_inspections(self, status_filter: str = None, type_filter: str = None) -> List[Dict]:
        """Get equipment list with last inspection data in a single optimized query"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = """
                SELECT e.*, et.description as type_description,
                       li.inspection_date as last_inspection_date,
                       li.result as last_inspection_result,
                       li.inspector_name as last_inspector_name,
                       li.notes as last_inspection_notes
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                LEFT JOIN (
                    SELECT DISTINCT ON (equipment_id) 
                           equipment_id, inspection_date, result, inspector_name, notes
                    FROM Inspections 
                    ORDER BY equipment_id, inspection_date DESC
                ) li ON e.equipment_id = li.equipment_id
                WHERE 1=1
            """
            params = []

            if status_filter:
                query += " AND e.status = %s"
                params.append(status_filter)

            if type_filter:
                query += " AND e.equipment_type = %s"
                params.append(type_filter)

            query += " ORDER BY e.equipment_type, e.equipment_id"

            cursor.execute(query, params)
            equipment_list = [dict(row) for row in cursor.fetchall()]

            # Convert last inspection data to nested dict format for compatibility
            for equipment in equipment_list:
                if equipment['last_inspection_date']:
                    equipment['last_inspection'] = {
                        'inspection_date': equipment['last_inspection_date'],
                        'result': equipment['last_inspection_result'],
                        'inspector_name': equipment['last_inspector_name'],
                        'notes': equipment['last_inspection_notes']
                    }
                else:
                    equipment['last_inspection'] = None

                # Remove the flattened fields to maintain clean structure
                for key in ['last_inspection_date', 'last_inspection_result', 'last_inspector_name', 'last_inspection_notes']:
                    equipment.pop(key, None)

            return equipment_list
        finally:
            conn.close()

    def delete_equipment(self, equipment_id: str) -> bool:
        """Delete equipment entry (only if no inspections exist)"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Check if equipment has inspections
            cursor.execute("SELECT COUNT(*) FROM Inspections WHERE equipment_id = %s", (equipment_id,))
            inspection_count = cursor.fetchone()[0]

            if inspection_count > 0:
                return False  # Cannot delete equipment with inspections

            # Delete status changes first (foreign key constraint)
            cursor.execute("DELETE FROM Status_Changes WHERE equipment_id = %s", (equipment_id,))

            # Delete equipment
            cursor.execute("DELETE FROM Equipment WHERE equipment_id = %s", (equipment_id,))

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """Get equipment details by ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT e.*, et.description as type_description, et.is_soft_goods, et.lifespan_years
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE e.equipment_id = %s
            """, (equipment_id,))

            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()

    def update_equipment_status(self, equipment_id: str, new_status: str) -> bool:
        """Update equipment status and record the change"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Get current status
            cursor.execute("SELECT status FROM Equipment WHERE equipment_id = %s", (equipment_id,))
            result = cursor.fetchone()
            if not result:
                return False

            old_status = result[0]

            # Update equipment status
            cursor.execute("""
                UPDATE Equipment SET status = %s WHERE equipment_id = %s
            """, (new_status, equipment_id))

            # Record status change
            red_tag_date = date.today() if new_status == 'RED_TAGGED' else None
            cursor.execute("""
                INSERT INTO Status_Changes (equipment_id, old_status, new_status, red_tag_date)
                VALUES (%s, %s, %s, %s)
            """, (equipment_id, old_status, new_status, red_tag_date))

            conn.commit()
            return True
        finally:
            conn.close()

    def update_equipment_service_date(self, equipment_id: str, date_put_in_service: date) -> bool:
        """Update the date put in service for equipment"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Equipment 
                SET date_put_in_service = %s
                WHERE equipment_id = %s
            """, (date_put_in_service, equipment_id))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"Error updating equipment service date: {e}")
            return False
        finally:
            conn.close()

    def update_equipment_info(self, equipment_id: str, name: str = None, serial_number: str = None) -> bool:
        """Update equipment name and serial number"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Equipment 
                SET name = %s, serial_number = %s
                WHERE equipment_id = %s
            """, (name, serial_number, equipment_id))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"Error updating equipment info: {e}")
            return False
        finally:
            conn.close()

    def add_inspection(self, equipment_id: str, inspection_date: date, result: str, 
                      inspector_name: str, notes: str = None) -> int:
        """Add inspection record and update equipment status if failed"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Insert inspection
            cursor.execute("""
                INSERT INTO Inspections (equipment_id, inspection_date, result, inspector_name, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING inspection_id
            """, (equipment_id, inspection_date, result, inspector_name, notes))

            inspection_id = cursor.fetchone()[0]

            # If failed inspection, red tag the equipment
            if result == 'FAIL':
                self.update_equipment_status(equipment_id, 'RED_TAGGED')

            conn.commit()
            return inspection_id
        finally:
            conn.close()

    def get_equipment_inspections(self, equipment_id: str) -> List[Dict]:
        """Get all inspections for equipment"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM Inspections 
                WHERE equipment_id = %s 
                ORDER BY inspection_date DESC
            """, (equipment_id,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_last_inspection(self, equipment_id: str) -> Optional[Dict]:
        """Get most recent inspection for equipment"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM Inspections 
                WHERE equipment_id = %s 
                ORDER BY inspection_date DESC LIMIT 1
            """, (equipment_id,))

            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()

    # Equipment Types operations
    def get_equipment_types(self, active_only: bool = True) -> List[Dict]:
        """Get equipment types"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = "SELECT * FROM Equipment_Types"
            if active_only:
                query += " WHERE is_active = TRUE"
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
            result = cursor.fetchone()
            max_sort = result[0] if result[0] is not None else 0

            cursor.execute("""
                INSERT INTO Equipment_Types 
                (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (type_code, description, is_soft_goods, lifespan_years, inspection_interval_months, max_sort + 1))

            conn.commit()
            return True
        except psycopg2.IntegrityError:
            return False
        finally:
            conn.close()

    def update_equipment_type(self, type_code: str, description: str, is_soft_goods: bool = False,
                             lifespan_years: int = None, inspection_interval_months: int = 6) -> bool:
        """Update equipment type"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Equipment_Types 
                SET description = %s, is_soft_goods = %s, lifespan_years = %s, inspection_interval_months = %s
                WHERE type_code = %s
            """, (description, is_soft_goods, lifespan_years, inspection_interval_months, type_code))

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def deactivate_equipment_type(self, type_code: str) -> bool:
        """Deactivate equipment type (soft delete)"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Equipment_Types SET is_active = FALSE WHERE type_code = %s
            """, (type_code,))

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # Reporting queries
    def get_overdue_inspections(self) -> List[Dict]:
        """Get equipment with overdue inspections"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       e.status, i.inspection_date as last_inspection_date,
                       et.inspection_interval_months,
                       (i.inspection_date + INTERVAL '1 month' * et.inspection_interval_months) as next_due_date
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
                    (i.inspection_date + INTERVAL '1 month' * et.inspection_interval_months) < CURRENT_DATE
                )
                ORDER BY i.inspection_date ASC NULLS FIRST
            """)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_red_tagged_equipment(self) -> List[Dict]:
        """Get red tagged equipment with days remaining"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       sc.red_tag_date,
                       (sc.red_tag_date + INTERVAL '30 days') as destroy_by_date,
                       EXTRACT(days FROM (sc.red_tag_date + INTERVAL '30 days') - CURRENT_DATE) as days_remaining
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       e.first_use_date,
                       (e.first_use_date + INTERVAL '1 year' * et.lifespan_years) as expiry_date,
                       EXTRACT(days FROM (e.first_use_date + INTERVAL '1 year' * et.lifespan_years) - CURRENT_DATE) as days_remaining
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE e.status = 'ACTIVE'
                AND et.is_soft_goods = TRUE
                AND e.first_use_date IS NOT NULL
                AND et.lifespan_years IS NOT NULL
                AND (e.first_use_date + INTERVAL '1 year' * et.lifespan_years) > CURRENT_DATE
                AND (e.first_use_date + INTERVAL '1 year' * et.lifespan_years) <= CURRENT_DATE + INTERVAL '1 year'
                ORDER BY expiry_date ASC
            """)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def export_to_csv(self, table_name: str, filename: str) -> bool:
        """Export table data to CSV"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if table_name == "equipment_summary":
                cursor.execute("""
                    SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                           e.name, e.serial_number, e.date_added_to_inventory, e.date_put_in_service, e.status,
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
                if cursor.description:
                    fieldnames = [desc[0] for desc in cursor.description]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for row in cursor.fetchall():
                        # Convert date objects to strings for CSV
                        csv_row = {}
                        for key, value in dict(row).items():
                            if isinstance(value, (date, datetime)):
                                csv_row[key] = value.strftime('%Y-%m-%d') if isinstance(value, date) else value.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                csv_row[key] = value
                        writer.writerow(csv_row)

            return True
        except Exception:
            return False
        finally:
            conn.close()

    # Job Management Methods
    def add_job(self, customer_name: str, description: str = None, projected_start_date: date = None, 
                projected_end_date: date = None, location_city: str = None, location_state: str = None,
                job_title: str = None) -> str:
        """Add new job and return the generated job ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Generate next job ID
            job_id = self._generate_job_id()

            cursor.execute("""
                INSERT INTO Jobs (job_id, customer_name, description, projected_start_date, 
                                projected_end_date, location_city, location_state, job_title)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (job_id, customer_name, description, projected_start_date, 
                  projected_end_date, location_city, location_state, job_title))

            # Create default billing record
            cursor.execute("""
                INSERT INTO Job_Billing (job_id)
                VALUES (%s)
            """, (job_id,))

            conn.commit()
            return job_id
        finally:
            conn.close()

    def _generate_job_id(self) -> str:
        """Generate next available job ID in format A000, A001, etc."""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT job_id FROM Jobs 
                WHERE job_id ~ '^A[0-9]{3}$'
                ORDER BY job_id DESC 
                LIMIT 1
            """)

            result = cursor.fetchone()
            if result:
                # Extract number and increment
                last_id = result[0]
                number = int(last_id[1:]) + 1
            else:
                # First job starts at A000
                number = 0

            return f"A{number:03d}"
        finally:
            conn.close()

    def get_jobs_list(self, status_filter: str = None) -> List[Dict]:
        """Get list of jobs with optional status filter"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if status_filter and status_filter != 'All':
                cursor.execute("""
                    SELECT j.*, jb.bid_amount, jb.actual_cost, jb.payment_status
                    FROM Jobs j
                    LEFT JOIN Job_Billing jb ON j.job_id = jb.job_id
                    WHERE j.status = %s
                    ORDER BY j.created_at DESC
                """, (status_filter,))
            else:
                cursor.execute("""
                    SELECT j.*, jb.bid_amount, jb.actual_cost, jb.payment_status
                    FROM Jobs j
                    LEFT JOIN Job_Billing jb ON j.job_id = jb.job_id
                    ORDER BY j.created_at DESC
                """)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_job_by_id(self, job_id: str) -> Optional[Dict]:
        """Get job details by ID"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT j.*, jb.billing_id, jb.bid_amount, jb.actual_cost, 
                       jb.payment_status, jb.invoice_date, jb.notes as billing_notes
                FROM Jobs j
                LEFT JOIN Job_Billing jb ON j.job_id = jb.job_id
                WHERE j.job_id = %s
            """, (job_id,))

            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()

    def update_job(self, job_id: str, customer_name: str, description: str = None,
                   projected_start_date: date = None, projected_end_date: date = None,
                   location_city: str = None, location_state: str = None,
                   job_title: str = None, status: str = None) -> bool:
        """Update job details"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Build dynamic update query
            update_fields = []
            values = []

            if customer_name is not None:
                update_fields.append("customer_name = %s")
                values.append(customer_name)
            if description is not None:
                update_fields.append("description = %s")
                values.append(description)
            if projected_start_date is not None:
                update_fields.append("projected_start_date = %s")
                values.append(projected_start_date)
            if projected_end_date is not None:
                update_fields.append("projected_end_date = %s")
                values.append(projected_end_date)
            if location_city is not None:
                update_fields.append("location_city = %s")
                values.append(location_city)
            if location_state is not None:
                update_fields.append("location_state = %s")
                values.append(location_state)
            if job_title is not None:
                update_fields.append("job_title = %s")
                values.append(job_title)
            if status is not None:
                update_fields.append("status = %s")
                values.append(status)

            if not update_fields:
                return True  # Nothing to update

            values.append(job_id)

            cursor.execute(f"""
                UPDATE Jobs 
                SET {', '.join(update_fields)}
                WHERE job_id = %s
            """, values)

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_job_billing(self, job_id: str, bid_amount: Decimal = None, actual_cost: Decimal = None,
                          payment_status: str = None, invoice_date: date = None, notes: str = None) -> bool:
        """Update job billing information"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # Build dynamic update query
            update_fields = []
            values = []

            if bid_amount is not None:
                update_fields.append("bid_amount = %s")
                values.append(bid_amount)
            if actual_cost is not None:
                update_fields.append("actual_cost = %s")
                values.append(actual_cost)
            if payment_status is not None:
                update_fields.append("payment_status = %s")
                values.append(payment_status)
            if invoice_date is not None:
                update_fields.append("invoice_date = %s")
                values.append(invoice_date)
            if notes is not None:
                update_fields.append("notes = %s")
                values.append(notes)

            if not update_fields:
                return True  # Nothing to update

            values.append(job_id)

            cursor.execute(f"""
                UPDATE Job_Billing 
                SET {', '.join(update_fields)}
                WHERE job_id = %s
            """, values)

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_active_jobs(self) -> List[Dict]:
        """Get list of jobs with ACTIVE status for equipment assignment"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT job_id, customer_name, job_title
                FROM Jobs
                WHERE status = 'ACTIVE'
                ORDER BY customer_name, job_title
            """)

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def assign_equipment_to_job(self, equipment_ids: List[str], job_id: str) -> int:
        """Assign multiple equipment items to a job, returns count of successful assignments"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            success_count = 0

            for equipment_id in equipment_ids:
                # Check if equipment can be assigned (ACTIVE or WAREHOUSE status)
                cursor.execute("""
                    SELECT status FROM Equipment 
                    WHERE equipment_id = %s AND status IN ('ACTIVE', 'WAREHOUSE')
                """, (equipment_id,))

                if cursor.fetchone():
                    # Update equipment status and assign to job
                    cursor.execute("""
                        UPDATE Equipment 
                        SET status = 'IN_FIELD', job_id = %s
                        WHERE equipment_id = %s
                    """, (job_id, equipment_id))

                    if cursor.rowcount > 0:
                        success_count += 1

            conn.commit()
            return success_count
        finally:
            conn.close()

    def get_job_equipment(self, job_id: str) -> List[Dict]:
        """Get all equipment assigned to a specific job"""
        conn = self.connect()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT e.equipment_id, e.equipment_type, et.description as type_description,
                       e.name, e.serial_number, e.status, e.date_put_in_service
                FROM Equipment e
                JOIN Equipment_Types et ON e.equipment_type = et.type_code
                WHERE e.job_id = %s
                ORDER BY e.equipment_type, e.equipment_id
            """, (job_id,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def return_equipment_from_job(self, equipment_ids: List[str]) -> int:
        """Return multiple equipment items from job, returns count of successful returns"""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            success_count = 0

            for equipment_id in equipment_ids:
                # Check if equipment is currently IN_FIELD
                cursor.execute("""
                    SELECT status FROM Equipment 
                    WHERE equipment_id = %s AND status = 'IN_FIELD'
                """, (equipment_id,))

                if cursor.fetchone():
                    # Return equipment to ACTIVE status and clear job assignment
                    cursor.execute("""
                        UPDATE Equipment 
                        SET status = 'ACTIVE', job_id = NULL
                        WHERE equipment_id = %s
                    """, (equipment_id,))

                    if cursor.rowcount > 0:
                        success_count += 1

            conn.commit()
            return success_count
        finally:
            conn.close()

    def get_job_stats(self) -> Dict:
        """Get job statistics for dashboard"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            stats = {
                'total': 0,
                'pending': 0,
                'bid_submitted': 0,
                'active': 0,
                'completed': 0,
                'cancelled': 0
            }

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM Jobs
                GROUP BY status
            """)

            for row in cursor.fetchall():
                status, count = row
                stats['total'] += count
                if status == 'PENDING':
                    stats['pending'] = count
                elif status == 'BID_SUBMITTED':
                    stats['bid_submitted'] = count
                elif status == 'ACTIVE':
                    stats['active'] = count
                elif status == 'COMPLETED':
                    stats['completed'] = count
                elif status == 'CANCELLED':
                    stats['cancelled'] = count

            return stats
        finally:
            conn.close()