# Equipment Inventory Management System

## Overview
This project is a web-based equipment inventory management system specifically designed for safety and climbing equipment. Its core purpose is to provide comprehensive tracking of equipment with unique IDs, manage mandatory inspection cycles, control equipment status, and ensure compliance with safety regulations, including 7-year record retention requirements. The system allows users to manage the complete equipment lifecycle from creation to disposal, maintaining full audit trails. The vision is to streamline equipment management for safety-critical environments, ensuring compliance and enhancing operational efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The system utilizes a Flask web application with Bootstrap 5 for the UI framework, focusing on server-side rendered web pages with a responsive design. It employs a base template with extending pages for forms and reports, and modular HTML templates with JavaScript enhancements for interactivity.

### Technical Implementations
- **Backend Language**: Python 3.
- **Database**: PostgreSQL is used as the primary database, managed through a Data Access Object (DAO) pattern with a centralized DatabaseManager.
- **Data Models**: Dataclass-based models are used, separating business logic from data representation.
- **Authentication**: Magic link email-based authentication is implemented with role-based access control. The system features a multi-role security model distinguishing between admin and technician users, with session-based authentication and automatic token expiry. All routes are protected with role-specific permissions.
- **Document Management System**: Handles document oversight, user-specific document management, secure file uploads (PDF, DOC, DOCX, TXT, JPG, PNG, GIF up to 10MB), document bundling for PDF generation, inline document renaming with security validation, and role-based access control for documents.
- **Core Business Logic**: Includes equipment status enumeration (ACTIVE, RED_TAGGED, DESTROYED), inspection result tracking (PASS, FAIL), and dataclasses for Equipment and EquipmentType with validation logic.
- **Key Features**:
    - Comprehensive equipment tracking with unique IDs and names.
    - Management of 6-month inspection cycles and 30-day red tag durations.
    - Lifecycle management including creation, service date tracking, and disposal.
    - Batch equipment creation and collapsible grouping by type prefix.
    - PDF export functionality for inventory and selected items.
    - Invoice generation and management with status tracking (DRAFT, SENT, PAID).
    - Job management with deletion features for non-active jobs.
    - Compliance management with 7-year record retention and audit trails for status changes and inspections.
    - Document renaming functionality with inline editing, security validation, and extension preservation.

### System Design Choices
- **Design Pattern**: Data Access Object (DAO) pattern for database interactions.
- **Scalability Considerations**: Designed for eventual authentication system expansion, cloud storage integration, and potential multi-tenant support.
- **Business Rules**:
    - Unique ID format validation ([TYPE]/[001-999]).
    - Mandatory 6-month inspection cycles.
    - Maximum 30-day red tag duration.
    - 10-year lifespan for soft goods from first use; unlimited for hardware (inspection-dependent).
    - Automatic 7-year record retention.
    - Status change audit trails and inspection result tracking.

## External Dependencies

- **Database**: PostgreSQL
- **Web Framework**: Flask
- **UI Framework**: Bootstrap 5
- **Production Server**: Gunicorn
- **Email Service**: Resend API (for magic link authentication)