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
- **Current State**: Magic link email-based authentication implemented
- **Security Model**: Single shared business inventory system with email authentication
- **Data Protection**: Session-based authentication with automatic token expiry (1 hour)
- **Access Control**: All routes protected except login/verify endpoints

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
- **July 15, 2025**: Implemented magic link authentication system for secure access
- **July 15, 2025**: Added login/logout functionality with email-based authentication
- **July 15, 2025**: Protected all routes with authentication requirements
- **July 15, 2025**: Created single shared business inventory system (no separate user sessions)
- **July 15, 2025**: Fixed magic link authentication system - form submission now works properly
- **July 15, 2025**: Debugged Resend API integration - requires real email addresses (not test domains)
- **July 15, 2025**: Fixed deployment configuration - replaced generic $file variable with specific app.py reference
- **July 15, 2025**: Added production-ready Flask configuration with environment variable support for PORT
- **July 15, 2025**: Implemented Gunicorn production server with proper configuration
- **July 15, 2025**: Added health check endpoint (/health) for deployment monitoring and status verification
- **July 15, 2025**: Created Procfile and production startup scripts for cloud deployment
- **July 15, 2025**: Fixed Flask app deployment issues with proper database initialization sequence
- **July 15, 2025**: Added robust error handling for PostgreSQL connection during startup
- **July 15, 2025**: Created WSGI entry point (wsgi.py) for production deployment compatibility
- **July 15, 2025**: Enhanced startup logging and environment variable validation
- **July 15, 2025**: Verified all database tables create successfully (equipment, equipment_types, inspections, status_changes, auth_tokens)
- **July 15, 2025**: Completely removed "purchase date" field from entire system per user request
- **July 15, 2025**: Added comprehensive PDF export functionality with complete inventory and selective item export options
- **July 15, 2025**: Updated date system: replaced "first use date" with "date added to inventory" and "date put in service"
- **July 15, 2025**: Implemented updateable service date functionality - equipment can be put in service after being added to inventory
- **July 15, 2025**: Enhanced equipment details page with service date management form
- **July 15, 2025**: Updated PDF exports to include new date fields and proper column formatting
- **July 15, 2025**: Added bulk "Put in Service" functionality using checkbox selection from main equipment list
- **July 15, 2025**: Created modal interface for bulk service date updates with date picker
- **July 15, 2025**: Implemented efficient workflow for putting multiple equipment items in service simultaneously
- **July 28, 2025**: Fixed template errors in add_inspection.html and updated status logic for equipment inspections
- **July 28, 2025**: Updated inspection button logic to support ACTIVE, IN_FIELD, and WAREHOUSE equipment statuses
- **July 28, 2025**: Enhanced equipment status mapping with proper icons and colors for all status types
- **July 28, 2025**: Implemented comprehensive invoice generation system with PostgreSQL backend
- **July 28, 2025**: Created Invoices and Invoice_Line_Items database tables with proper relationships
- **July 28, 2025**: Added complete invoice management functionality: create, view, edit, delete, and status tracking
- **July 28, 2025**: Built professional invoice templates with clean design and print functionality
- **July 28, 2025**: Integrated invoice generation from job details page with automatic equipment context
- **July 28, 2025**: Added invoice management dashboard with status filtering and summary statistics
- **July 28, 2025**: Added "Invoices" menu item to main navigation for easy access

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