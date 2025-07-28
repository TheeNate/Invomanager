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
    
    def create_job_equipment_pdf(self, job: Dict, equipment_list: List[Dict], 
                               title: str = "Job Equipment Report") -> bytes:
        """Create PDF with equipment assigned to a specific job"""
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
        
        # Job Information Section
        job_info_text = f"""
        <b>Job ID:</b> {job.get('job_id', 'Unknown')}<br/>
        <b>Customer:</b> {job.get('customer_name', 'Not specified')}<br/>
        <b>Job Title:</b> {job.get('job_title', 'Not specified')}<br/>
        <b>Status:</b> {job.get('status', 'Unknown')}<br/>
        <b>Location:</b> {self._format_job_location(job)}<br/>
        <b>Start Date:</b> {self._format_date(job.get('projected_start_date'))}<br/>
        <b>End Date:</b> {self._format_date(job.get('projected_end_date'))}<br/>
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        story.append(Paragraph(job_info_text, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Equipment section
        equipment_count = len(equipment_list)
        equipment_header = f"Assigned Equipment ({equipment_count} items)"
        story.append(Paragraph(equipment_header, self.header_style))
        story.append(Spacer(1, 10))
        
        if equipment_list:
            # Create equipment table
            table_data = [
                ['Equipment ID', 'Type', 'Name', 'Serial Number', 'Status', 'Service Date']
            ]
            
            for item in sorted(equipment_list, key=lambda x: x.get('equipment_id', '')):
                service_date = self._format_date(item.get('date_put_in_service'))
                
                table_data.append([
                    item.get('equipment_id', ''),
                    f"{item.get('equipment_type', '')} - {item.get('type_description', '')}",
                    item.get('name', 'Not specified'),
                    item.get('serial_number', 'Not specified'),
                    self._format_status(item.get('status', 'Unknown')),
                    service_date
                ])
            
            # Create and style table
            table = Table(table_data, colWidths=[1.2*inch, 1.8*inch, 1.5*inch, 1.2*inch, 0.8*inch, 1*inch])
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
        else:
            story.append(Paragraph("No equipment assigned to this job.", self.styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"Equipment Inventory Management System - Job Equipment Report"
        story.append(Paragraph(footer_text, self.footer_style))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_job_location(self, job: Dict) -> str:
        """Format job location for display"""
        city = job.get('location_city', '')
        state = job.get('location_state', '')
        
        if city and state:
            return f"{city}, {state}"
        elif city:
            return city
        elif state:
            return state
        else:
            return "Not specified"
    
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

def generate_invoice_pdf(invoice: Dict) -> io.BytesIO:
    """Generate PDF for a single invoice"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20,
        textColor=HexColor('#2c3e50'),
        alignment=TA_LEFT
    )
    
    header_style = ParagraphStyle(
        'InvoiceHeader',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=10,
        textColor=HexColor('#2c3e50'),
        alignment=TA_LEFT
    )
    
    # Title
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 12))
    
    # Invoice header information
    header_data = [
        ["Invoice Number:", invoice.get('invoice_number', 'N/A')],
        ["Invoice Date:", invoice.get('invoice_date', date.today()).strftime('%B %d, %Y') if invoice.get('invoice_date') else 'N/A'],
        ["Status:", invoice.get('status', 'DRAFT')]
    ]
    
    if invoice.get('job_number'):
        header_data.append(["Job Number:", invoice['job_number']])
    
    header_table = Table(header_data, colWidths=[1.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Billing information section
    billing_data = []
    
    # Bill To and Pay To side by side
    bill_to_text = "Bill To:<br/>"
    if invoice.get('issued_to_name'):
        bill_to_text += f"{invoice['issued_to_name']}<br/>"
    if invoice.get('issued_to_company'):
        bill_to_text += f"{invoice['issued_to_company']}<br/>"
    if invoice.get('issued_to_address'):
        # Replace \n with <br/> for proper line breaks in PDF
        address = invoice['issued_to_address'].replace('\n', '<br/>')
        bill_to_text += f"{address}<br/>"
    
    pay_to_text = "Pay To:<br/>"
    if invoice.get('pay_to_name'):
        pay_to_text += f"{invoice['pay_to_name']}<br/>"
    if invoice.get('pay_to_company'):
        pay_to_text += f"{invoice['pay_to_company']}<br/>"
    if invoice.get('pay_to_address'):
        # Replace \n with <br/> for proper line breaks in PDF
        address = invoice['pay_to_address'].replace('\n', '<br/>')
        pay_to_text += f"{address}<br/>"
    
    billing_table = Table([[Paragraph(bill_to_text, styles['Normal']), 
                           Paragraph(pay_to_text, styles['Normal'])]], 
                          colWidths=[3*inch, 3*inch])
    billing_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, black),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(billing_table)
    story.append(Spacer(1, 20))
    
    # Equipment context (if applicable)
    if invoice.get('equipment_id'):
        context_text = f"Equipment Context: {invoice['equipment_id']}"
        if invoice.get('equipment_name'):
            context_text += f" - {invoice['equipment_name']}"
        if invoice.get('equipment_type'):
            context_text += f" ({invoice['equipment_type']})"
        
        story.append(Paragraph(context_text, header_style))
        story.append(Spacer(1, 12))
    
    # Line items table
    line_items_data = [['Description', 'Unit Price', 'Quantity', 'Total']]
    
    for item in invoice.get('line_items', []):
        line_items_data.append([
            item.get('description', ''),
            f"${item.get('unit_price', 0):.2f}",
            str(item.get('quantity', 0)),
            f"${item.get('line_total', 0):.2f}"
        ])
    
    line_items_table = Table(line_items_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
    line_items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Description left-aligned
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(line_items_table)
    story.append(Spacer(1, 20))
    
    # Totals section
    totals_data = []
    totals_data.append(['Subtotal:', f"${invoice.get('subtotal', 0):.2f}"])
    
    if invoice.get('tax_rate', 0) > 0:
        totals_data.append([f"Tax ({invoice.get('tax_rate', 0):.1f}%):", f"${invoice.get('tax_amount', 0):.2f}"])
    
    totals_data.append(['Total:', f"${invoice.get('total_amount', 0):.2f}"])
    
    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Bold total row
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('LINEABOVE', (0, -1), (-1, -1), 2, black),  # Line above total
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(totals_table)
    
    # Footer
    story.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#7f8c8d'),
        alignment=TA_CENTER
    )))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer