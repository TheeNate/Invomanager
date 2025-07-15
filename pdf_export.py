#!/usr/bin/env python3
"""
PDF Export functionality for Equipment Inventory Management System
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, lightgrey
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, date
from typing import List, Dict, Optional
import io

class EquipmentPDFExporter:
    """PDF export functionality for equipment inventory"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=16,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=TA_CENTER
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=20,
            textColor=HexColor('#34495e'),
            alignment=TA_CENTER
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading3'],
            fontSize=10,
            spaceAfter=10,
            textColor=HexColor('#2c3e50'),
            alignment=TA_LEFT
        )
        
        # Footer style
        self.footer_style = ParagraphStyle(
            'CustomFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=HexColor('#7f8c8d'),
            alignment=TA_CENTER
        )
    
    def create_complete_inventory_pdf(self, equipment_list: List[Dict], 
                                   title: str = "Complete Equipment Inventory") -> bytes:
        """Create PDF with complete equipment inventory"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build the PDF content
        story = []
        
        # Title
        story.append(Paragraph(title, self.title_style))
        story.append(Spacer(1, 20))
        
        # Subtitle with date and stats
        total_items = len(equipment_list)
        active_items = len([eq for eq in equipment_list if eq.get('status') == 'ACTIVE'])
        red_tagged = len([eq for eq in equipment_list if eq.get('status') == 'RED_TAGGED'])
        destroyed = len([eq for eq in equipment_list if eq.get('status') == 'DESTROYED'])
        
        subtitle_text = f"""
        Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 
        Total Items: {total_items} | 
        Active: {active_items} | 
        Red Tagged: {red_tagged} | 
        Destroyed: {destroyed}
        """
        story.append(Paragraph(subtitle_text, self.subtitle_style))
        story.append(Spacer(1, 20))
        
        # Group equipment by type
        equipment_by_type = {}
        for equipment in equipment_list:
            eq_type = equipment.get('equipment_type', 'Unknown')
            if eq_type not in equipment_by_type:
                equipment_by_type[eq_type] = []
            equipment_by_type[eq_type].append(equipment)
        
        # Create table for each equipment type
        for eq_type, items in sorted(equipment_by_type.items()):
            if not items:
                continue
                
            # Type header
            type_description = items[0].get('type_description', 'Unknown Type')
            header_text = f"{eq_type} - {type_description} ({len(items)} items)"
            story.append(Paragraph(header_text, self.header_style))
            story.append(Spacer(1, 10))
            
            # Create table data
            table_data = [
                ['Equipment ID', 'Name', 'Serial Number', 'Status', 'Added to Inventory', 'Put in Service', 'Last Inspection']
            ]
            
            for item in sorted(items, key=lambda x: x.get('equipment_id', '')):
                # Format dates
                date_added = self._format_date(item.get('date_added_to_inventory'))
                date_in_service = self._format_date(item.get('date_put_in_service'))
                last_inspection = self._format_inspection_info(item.get('last_inspection'))
                
                table_data.append([
                    item.get('equipment_id', ''),
                    item.get('name', 'Not specified'),
                    item.get('serial_number', 'Not specified'),
                    self._format_status(item.get('status', 'Unknown')),
                    date_added,
                    date_in_service,
                    last_inspection
                ])
            
            # Create and style table
            table = Table(table_data, colWidths=[1*inch, 1.2*inch, 1*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1.2*inch])
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#dee2e6')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        # Footer
        footer_text = f"Equipment Inventory Management System - Page <seq id='page_num'> of <seqReset id='page_num'>"
        story.append(Paragraph(footer_text, self.footer_style))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def create_selected_equipment_pdf(self, equipment_list: List[Dict], 
                                    equipment_ids: List[str],
                                    title: str = "Selected Equipment Report") -> bytes:
        """Create PDF with selected equipment items"""
        # Filter equipment by selected IDs
        selected_equipment = [eq for eq in equipment_list if eq.get('equipment_id') in equipment_ids]
        
        if not selected_equipment:
            selected_equipment = [{'equipment_id': 'No items selected', 'name': '', 'serial_number': '', 'status': '', 'first_use_date': '', 'last_inspection': None}]
        
        return self.create_complete_inventory_pdf(selected_equipment, title)
    
    def _format_date(self, date_value) -> str:
        """Format date for display"""
        if not date_value:
            return 'Not specified'
        
        if isinstance(date_value, str):
            try:
                parsed_date = datetime.strptime(date_value, '%Y-%m-%d').date()
                return parsed_date.strftime('%Y-%m-%d')
            except:
                return date_value
        elif isinstance(date_value, (date, datetime)):
            return date_value.strftime('%Y-%m-%d')
        
        return 'Not specified'
    
    def _format_status(self, status: str) -> str:
        """Format status for display"""
        status_map = {
            'ACTIVE': 'Active',
            'RED_TAGGED': 'Red Tagged',
            'DESTROYED': 'Destroyed'
        }
        return status_map.get(status, status)
    
    def _format_inspection_info(self, last_inspection: Optional[Dict]) -> str:
        """Format last inspection info"""
        if not last_inspection:
            return 'Never inspected'
        
        date_str = self._format_date(last_inspection.get('inspection_date'))
        result = last_inspection.get('result', 'Unknown')
        
        if date_str == 'Not specified':
            return 'Never inspected'
        
        return f"{date_str} ({result})"