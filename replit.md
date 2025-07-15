# Equipment Inventory Management System

## Overview

This is a web-based equipment inventory management system specifically designed for safety/climbing equipment. The application provides comprehensive tracking of equipment with unique IDs, mandatory inspection cycles, status management, and compliance with safety regulations including 7-year record retention requirements. Users can manage equipment lifecycle from creation to disposal with full audit trails.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Flask web application with Bootstrap 5 UI framework
- **Pattern**: Server-side rendered web pages with responsive design
- **Structure**: Base template with extending pages for forms and reports
- **Components**: Modular HTML templates with JavaScript enhancements for interactivity

### Backend Architecture
- **Language**: Python 3
- **Database**: PostgreSQL (cloud database with proper connection handling)
- **Pattern**: Data Access Object (DAO) pattern with centralized DatabaseManager
- **Models**: Dataclass-based models with business logic separation

### Data Storage Solutions
- **Primary Database**: PostgreSQL with the following key tables:
  - Equipment: Core equipment tracking with unique IDs, names, and status
  - Equipment_Types: Equipment categories with validation rules
  - Inspections: 6-month inspection cycle tracking
  - Status_Changes: Audit trail for equipment status changes
- **File Storage**: No external file dependencies, fully self-contained

### Authentication and Authorization
- **Current State**: No authentication system implemented
- **Security Model**: Desktop application assumes single-user environment
- **Data Protection**: File-based access control through OS permissions

## Key Components

### Database Layer (`database_postgres.py`)
- PostgreSQL connection management with environment variable configuration
- Database initialization and schema creation with proper constraints
- CRUD operations for all equipment data including name field
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

### Recent Changes
- **July 14, 2025**: Successfully upgraded from SQLite to PostgreSQL database
- **July 14, 2025**: Added Name column to equipment table between Equipment ID and Type
- **July 14, 2025**: Enhanced search functionality to include equipment names
- **July 14, 2025**: Updated all templates to display and input equipment names
- **July 14, 2025**: Added batch equipment creation functionality (2-50 items with individual serial numbers)
- **July 14, 2025**: Implemented collapsible equipment grouping by type prefix (C/001-300, D/001-75, etc.)
- **July 14, 2025**: Added expand/collapse all functionality for better navigation of large inventories

### Future Scalability
- Authentication system can be added for user management
- Cloud storage integration for data synchronization
- Multi-tenant support for organizations

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