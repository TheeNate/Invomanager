# Equipment Inventory Management System

## Overview

This is a desktop equipment inventory management system specifically designed for safety/climbing equipment. The application provides comprehensive tracking of equipment with unique IDs, mandatory inspection cycles, status management, and compliance with safety regulations including 7-year record retention requirements.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Tkinter (Python's built-in GUI library)
- **Pattern**: Traditional desktop application with multiple windows
- **Structure**: Main window with modal dialogs for forms and reports
- **Components**: Modular UI components in separate files for maintainability

### Backend Architecture
- **Language**: Python 3
- **Database**: SQLite (embedded database)
- **Pattern**: Data Access Object (DAO) pattern with centralized DatabaseManager
- **Models**: Dataclass-based models with business logic separation

### Data Storage Solutions
- **Primary Database**: SQLite with the following key tables:
  - Equipment: Core equipment tracking with unique IDs and status
  - Equipment_Types: Equipment categories with validation rules
  - Inspections: 6-month inspection cycle tracking
  - Status_Changes: Audit trail for equipment status changes
- **File Storage**: No external file dependencies, fully self-contained

### Authentication and Authorization
- **Current State**: No authentication system implemented
- **Security Model**: Desktop application assumes single-user environment
- **Data Protection**: File-based access control through OS permissions

## Key Components

### Database Layer (`database.py`)
- SQLite connection management with row factory for named column access
- Database initialization and schema creation
- CRUD operations for all equipment data
- Transaction management and connection pooling

### Business Logic (`models.py`)
- Equipment status enumeration (ACTIVE, RED_TAGGED, DESTROYED)
- Inspection result tracking (PASS, FAIL)
- Equipment and EquipmentType dataclasses with validation logic
- Business rule enforcement through model properties

### User Interface Layer (`ui/`)
- **MainWindow**: Primary application interface with equipment listing and filtering
- **EquipmentForm**: Add/edit equipment with validation
- **InspectionForm**: Record inspection results and manage compliance
- **EquipmentTypesForm**: Manage equipment categories and rules
- **ReportsWindow**: Compliance dashboards and overdue tracking

### Utilities (`utils/`)
- **Validators**: Form validation with custom error handling
- **Helpers**: Date formatting, type conversion, and UI utility functions

## Data Flow

1. **Equipment Creation**: User inputs equipment data → Form validation → Database insertion → UI refresh
2. **Inspection Recording**: Equipment selection → Inspection form → Business rule validation → Status updates → Compliance tracking
3. **Status Management**: Equipment selection → Status change → Audit logging → Timeline tracking
4. **Reporting**: Database queries → Data aggregation → Report generation → Export capabilities

## External Dependencies

### Core Dependencies
- **Python Standard Library**: tkinter, sqlite3, datetime, typing, dataclasses, enum
- **Database**: SQLite (embedded, no external server required)
- **UI Framework**: Tkinter (built-in, no additional installations)

### Development Dependencies
- No external package manager dependencies
- Self-contained application design
- Cross-platform compatibility through Python standard library

## Deployment Strategy

### Current Deployment
- **Target**: Desktop application for single-user environments
- **Distribution**: Python script execution
- **Requirements**: Python 3.7+ with standard library
- **Database**: Auto-created SQLite file in application directory

### Deployment Considerations
- No server infrastructure required
- Portable application with local data storage
- Manual backup/restore through SQLite file copying
- Cross-platform compatibility (Windows, macOS, Linux)

### Future Scalability
- Database can be migrated to PostgreSQL for multi-user support
- UI can be web-based for remote access
- Authentication system can be added for user management
- Cloud storage integration for data synchronization

## Business Rules Implementation

### Equipment Lifecycle
- Unique ID format validation ([TYPE]/[001-999])
- 6-month mandatory inspection cycles
- 30-day maximum red tag duration
- 10-year lifespan for soft goods from first use
- Unlimited lifespan for hardware (inspection-dependent)

### Compliance Management
- 7-year record retention automatically enforced
- Status change audit trail with timestamps
- Inspection result tracking with inspector attribution
- Automatic compliance violation detection and reporting