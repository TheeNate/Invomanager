"""
Reports window for Equipment Inventory Management System
Displays overdue inspections, red tag countdown, and expiring equipment
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
from database import DatabaseManager
from utils.helpers import format_date, get_urgency_level, get_urgency_color, days_between

class ReportsWindow:
    def __init__(self, parent: tk.Tk, db_manager: DatabaseManager):
        self.parent = parent
        self.db_manager = db_manager
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Equipment Reports Dashboard")
        self.window.geometry("1000x700")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center window
        self.center_window()
        
        # Initialize data
        self.overdue_data = []
        self.red_tagged_data = []
        self.expiring_data = []
        
        # Create UI
        self.create_widgets()
        self.setup_layout()
        
        # Load data
        self.refresh_all_reports()
    
    def center_window(self):
        """Center the window on parent"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create all UI widgets"""
        
        # Main frame
        self.main_frame = ttk.Frame(self.window)
        
        # Title and toolbar
        self.header_frame = ttk.Frame(self.main_frame)
        
        title_label = ttk.Label(
            self.header_frame, text="Equipment Reports Dashboard",
            font=('TkDefaultFont', 14, 'bold')
        )
        title_label.pack(side='left')
        
        # Toolbar buttons
        self.toolbar_frame = ttk.Frame(self.header_frame)
        self.toolbar_frame.pack(side='right')
        
        self.btn_refresh = ttk.Button(
            self.toolbar_frame, text="🔄 Refresh", 
            command=self.refresh_all_reports
        )
        self.btn_refresh.pack(side='left', padx=(0, 5))
        
        self.btn_export = ttk.Button(
            self.toolbar_frame, text="📄 Export Reports", 
            command=self.export_reports
        )
        self.btn_export.pack(side='left', padx=(0, 5))
        
        self.btn_close = ttk.Button(
            self.toolbar_frame, text="Close", 
            command=self.window.destroy
        )
        self.btn_close.pack(side='left')
        
        # Notebook for different reports
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Overdue Inspections Tab
        self.overdue_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overdue_frame, text="🔍 Overdue Inspections")
        
        # Red Tagged Equipment Tab
        self.red_tagged_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.red_tagged_frame, text="🔴 Red Tagged Equipment")
        
        # Expiring Equipment Tab
        self.expiring_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.expiring_frame, text="⏰ Expiring Equipment")
        
        # Summary Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="📊 Summary")
        
        # Create individual report sections
        self.create_overdue_report()
        self.create_red_tagged_report()
        self.create_expiring_report()
        self.create_summary_report()
    
    def create_overdue_report(self):
        """Create overdue inspections report"""
        # Info label
        info_label = ttk.Label(
            self.overdue_frame, 
            text="Equipment with overdue inspections (6+ months since last inspection)",
            font=('TkDefaultFont', 9, 'italic')
        )
        info_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        # Count label
        self.overdue_count_label = ttk.Label(
            self.overdue_frame, text="",
            font=('TkDefaultFont', 9, 'bold')
        )
        self.overdue_count_label.pack(anchor='w', padx=10, pady=(0, 5))
        
        # Treeview frame
        overdue_tree_frame = ttk.Frame(self.overdue_frame)
        overdue_tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Overdue treeview
        overdue_columns = ('Equipment ID', 'Type', 'Description', 'Last Inspection', 'Days Overdue', 'Urgency')
        self.overdue_tree = ttk.Treeview(
            overdue_tree_frame, columns=overdue_columns, show='headings', height=15
        )
        
        # Configure columns
        for col in overdue_columns:
            self.overdue_tree.heading(col, text=col)
        
        self.overdue_tree.column('Equipment ID', width=100)
        self.overdue_tree.column('Type', width=60)
        self.overdue_tree.column('Description', width=150)
        self.overdue_tree.column('Last Inspection', width=120)
        self.overdue_tree.column('Days Overdue', width=100)
        self.overdue_tree.column('Urgency', width=80)
        
        # Scrollbars
        overdue_scroll_y = ttk.Scrollbar(overdue_tree_frame, orient='vertical', command=self.overdue_tree.yview)
        self.overdue_tree.configure(yscrollcommand=overdue_scroll_y.set)
        
        overdue_scroll_x = ttk.Scrollbar(overdue_tree_frame, orient='horizontal', command=self.overdue_tree.xview)
        self.overdue_tree.configure(xscrollcommand=overdue_scroll_x.set)
        
        # Pack treeview and scrollbars
        self.overdue_tree.grid(row=0, column=0, sticky='nsew')
        overdue_scroll_y.grid(row=0, column=1, sticky='ns')
        overdue_scroll_x.grid(row=1, column=0, sticky='ew')
        
        overdue_tree_frame.grid_rowconfigure(0, weight=1)
        overdue_tree_frame.grid_columnconfigure(0, weight=1)
    
    def create_red_tagged_report(self):
        """Create red tagged equipment report"""
        # Info label
        info_label = ttk.Label(
            self.red_tagged_frame, 
            text="Red tagged equipment must be destroyed within 30 days",
            font=('TkDefaultFont', 9, 'italic')
        )
        info_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        # Count label
        self.red_tagged_count_label = ttk.Label(
            self.red_tagged_frame, text="",
            font=('TkDefaultFont', 9, 'bold')
        )
        self.red_tagged_count_label.pack(anchor='w', padx=10, pady=(0, 5))
        
        # Treeview frame
        red_tagged_tree_frame = ttk.Frame(self.red_tagged_frame)
        red_tagged_tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Red tagged treeview
        red_tagged_columns = ('Equipment ID', 'Type', 'Description', 'Red Tag Date', 'Destroy By', 'Days Remaining', 'Status')
        self.red_tagged_tree = ttk.Treeview(
            red_tagged_tree_frame, columns=red_tagged_columns, show='headings', height=15
        )
        
        # Configure columns
        for col in red_tagged_columns:
            self.red_tagged_tree.heading(col, text=col)
        
        self.red_tagged_tree.column('Equipment ID', width=100)
        self.red_tagged_tree.column('Type', width=60)
        self.red_tagged_tree.column('Description', width=150)
        self.red_tagged_tree.column('Red Tag Date', width=100)
        self.red_tagged_tree.column('Destroy By', width=100)
        self.red_tagged_tree.column('Days Remaining', width=100)
        self.red_tagged_tree.column('Status', width=80)
        
        # Scrollbars
        red_tagged_scroll_y = ttk.Scrollbar(red_tagged_tree_frame, orient='vertical', command=self.red_tagged_tree.yview)
        self.red_tagged_tree.configure(yscrollcommand=red_tagged_scroll_y.set)
        
        red_tagged_scroll_x = ttk.Scrollbar(red_tagged_tree_frame, orient='horizontal', command=self.red_tagged_tree.xview)
        self.red_tagged_tree.configure(xscrollcommand=red_tagged_scroll_x.set)
        
        # Pack treeview and scrollbars
        self.red_tagged_tree.grid(row=0, column=0, sticky='nsew')
        red_tagged_scroll_y.grid(row=0, column=1, sticky='ns')
        red_tagged_scroll_x.grid(row=1, column=0, sticky='ew')
        
        red_tagged_tree_frame.grid_rowconfigure(0, weight=1)
        red_tagged_tree_frame.grid_columnconfigure(0, weight=1)
    
    def create_expiring_report(self):
        """Create expiring soft goods report"""
        # Info label
        info_label = ttk.Label(
            self.expiring_frame, 
            text="Soft goods approaching 10-year expiration (within next 12 months)",
            font=('TkDefaultFont', 9, 'italic')
        )
        info_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        # Count label
        self.expiring_count_label = ttk.Label(
            self.expiring_frame, text="",
            font=('TkDefaultFont', 9, 'bold')
        )
        self.expiring_count_label.pack(anchor='w', padx=10, pady=(0, 5))
        
        # Treeview frame
        expiring_tree_frame = ttk.Frame(self.expiring_frame)
        expiring_tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Expiring treeview
        expiring_columns = ('Equipment ID', 'Type', 'Description', 'First Use Date', 'Expiry Date', 'Days Remaining', 'Priority')
        self.expiring_tree = ttk.Treeview(
            expiring_tree_frame, columns=expiring_columns, show='headings', height=15
        )
        
        # Configure columns
        for col in expiring_columns:
            self.expiring_tree.heading(col, text=col)
        
        self.expiring_tree.column('Equipment ID', width=100)
        self.expiring_tree.column('Type', width=60)
        self.expiring_tree.column('Description', width=150)
        self.expiring_tree.column('First Use Date', width=100)
        self.expiring_tree.column('Expiry Date', width=100)
        self.expiring_tree.column('Days Remaining', width=100)
        self.expiring_tree.column('Priority', width=80)
        
        # Scrollbars
        expiring_scroll_y = ttk.Scrollbar(expiring_tree_frame, orient='vertical', command=self.expiring_tree.yview)
        self.expiring_tree.configure(yscrollcommand=expiring_scroll_y.set)
        
        expiring_scroll_x = ttk.Scrollbar(expiring_tree_frame, orient='horizontal', command=self.expiring_tree.xview)
        self.expiring_tree.configure(xscrollcommand=expiring_scroll_x.set)
        
        # Pack treeview and scrollbars
        self.expiring_tree.grid(row=0, column=0, sticky='nsew')
        expiring_scroll_y.grid(row=0, column=1, sticky='ns')
        expiring_scroll_x.grid(row=1, column=0, sticky='ew')
        
        expiring_tree_frame.grid_rowconfigure(0, weight=1)
        expiring_tree_frame.grid_columnconfigure(0, weight=1)
    
    def create_summary_report(self):
        """Create summary dashboard"""
        # Summary frame with cards
        summary_content = ttk.Frame(self.summary_frame)
        summary_content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        summary_title = ttk.Label(
            summary_content, text="Equipment Status Summary",
            font=('TkDefaultFont', 16, 'bold')
        )
        summary_title.pack(pady=(0, 20))
        
        # Cards frame
        cards_frame = ttk.Frame(summary_content)
        cards_frame.pack(fill='x', pady=(0, 20))
        
        # Equipment status cards
        self.status_cards_frame = ttk.LabelFrame(cards_frame, text="Equipment Status Overview")
        self.status_cards_frame.pack(fill='x', pady=(0, 10))
        
        # Create status summary cards
        self.create_status_cards()
        
        # Critical alerts frame
        self.alerts_frame = ttk.LabelFrame(summary_content, text="🚨 Critical Alerts")
        self.alerts_frame.pack(fill='both', expand=True)
        
        # Alerts text widget
        self.alerts_text = tk.Text(
            self.alerts_frame, height=15, wrap='word',
            font=('TkDefaultFont', 10), state='disabled'
        )
        
        alerts_scroll = ttk.Scrollbar(self.alerts_frame, orient='vertical', command=self.alerts_text.yview)
        self.alerts_text.configure(yscrollcommand=alerts_scroll.set)
        
        self.alerts_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        alerts_scroll.pack(side='right', fill='y', pady=10)
    
    def create_status_cards(self):
        """Create equipment status summary cards"""
        # Clear existing cards
        for widget in self.status_cards_frame.winfo_children():
            widget.destroy()
        
        # Get equipment statistics
        try:
            all_equipment = self.db_manager.get_equipment_list()
            
            total_count = len(all_equipment)
            active_count = len([eq for eq in all_equipment if eq['status'] == 'ACTIVE'])
            red_tagged_count = len([eq for eq in all_equipment if eq['status'] == 'RED_TAGGED'])
            destroyed_count = len([eq for eq in all_equipment if eq['status'] == 'DESTROYED'])
            
            # Create cards
            cards_data = [
                ("Total Equipment", total_count, "#17a2b8"),
                ("Active", active_count, "#28a745"),
                ("Red Tagged", red_tagged_count, "#dc3545"),
                ("Destroyed", destroyed_count, "#6c757d")
            ]
            
            for i, (title, count, color) in enumerate(cards_data):
                card_frame = ttk.Frame(self.status_cards_frame)
                card_frame.grid(row=0, column=i, padx=10, pady=10, sticky='ew')
                
                # Title
                title_label = ttk.Label(
                    card_frame, text=title,
                    font=('TkDefaultFont', 9, 'bold')
                )
                title_label.pack()
                
                # Count
                count_label = ttk.Label(
                    card_frame, text=str(count),
                    font=('TkDefaultFont', 18, 'bold')
                )
                count_label.pack()
            
            # Configure grid weights
            for i in range(4):
                self.status_cards_frame.grid_columnconfigure(i, weight=1)
        
        except Exception as e:
            error_label = ttk.Label(
                self.status_cards_frame, 
                text=f"Error loading statistics: {str(e)}",
                foreground='red'
            )
            error_label.pack(padx=10, pady=10)
    
    def setup_layout(self):
        """Layout all widgets"""
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        self.header_frame.pack(fill='x', pady=(0, 10))
        
        # Notebook
        self.notebook.pack(fill='both', expand=True)
    
    def refresh_all_reports(self):
        """Refresh all report data"""
        try:
            # Load report data
            self.overdue_data = self.db_manager.get_overdue_inspections()
            self.red_tagged_data = self.db_manager.get_red_tagged_equipment()
            self.expiring_data = self.db_manager.get_expiring_soft_goods()
            
            # Populate reports
            self.populate_overdue_report()
            self.populate_red_tagged_report()
            self.populate_expiring_report()
            self.populate_summary_report()
            
            # Update status cards
            self.create_status_cards()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh reports: {str(e)}")
    
    def populate_overdue_report(self):
        """Populate overdue inspections report"""
        # Clear existing items
        for item in self.overdue_tree.get_children():
            self.overdue_tree.delete(item)
        
        # Update count label
        count = len(self.overdue_data)
        self.overdue_count_label.config(text=f"Found {count} equipment items with overdue inspections")
        
        # Add items
        for equipment in self.overdue_data:
            last_inspection_date = equipment.get('last_inspection_date')
            
            if last_inspection_date:
                # Parse the date string to date object
                if isinstance(last_inspection_date, str):
                    last_date = datetime.strptime(last_inspection_date, '%Y-%m-%d').date()
                else:
                    last_date = last_inspection_date
                
                days_overdue = days_between(last_date, date.today()) - 180  # 6 months = 180 days
                last_inspection_str = format_date(last_date)
            else:
                days_overdue = 999  # Never inspected
                last_inspection_str = "Never"
            
            urgency = get_urgency_level(days_overdue)
            
            values = (
                equipment['equipment_id'],
                equipment['equipment_type'],
                equipment['type_description'],
                last_inspection_str,
                str(max(0, days_overdue)),
                urgency
            )
            
            item = self.overdue_tree.insert('', 'end', values=values)
            
            # Color code by urgency
            if urgency == 'CRITICAL':
                self.overdue_tree.item(item, tags=('critical',))
            elif urgency == 'HIGH':
                self.overdue_tree.item(item, tags=('high',))
        
        # Configure tags
        self.overdue_tree.tag_configure('critical', background='#ffebee')
        self.overdue_tree.tag_configure('high', background='#fff3e0')
    
    def populate_red_tagged_report(self):
        """Populate red tagged equipment report"""
        # Clear existing items
        for item in self.red_tagged_tree.get_children():
            self.red_tagged_tree.delete(item)
        
        # Update count label
        count = len(self.red_tagged_data)
        self.red_tagged_count_label.config(text=f"Found {count} red tagged equipment items")
        
        # Add items
        for equipment in self.red_tagged_data:
            red_tag_date = equipment.get('red_tag_date')
            destroy_by_date = equipment.get('destroy_by_date')
            days_remaining = int(equipment.get('days_remaining', 0))
            
            # Status based on days remaining
            if days_remaining <= 0:
                status = "OVERDUE"
            elif days_remaining <= 7:
                status = "URGENT"
            else:
                status = "OK"
            
            values = (
                equipment['equipment_id'],
                equipment['equipment_type'],
                equipment['type_description'],
                format_date(red_tag_date),
                format_date(destroy_by_date),
                str(max(0, days_remaining)),
                status
            )
            
            item = self.red_tagged_tree.insert('', 'end', values=values)
            
            # Color code by status
            if status == 'OVERDUE':
                self.red_tagged_tree.item(item, tags=('overdue',))
            elif status == 'URGENT':
                self.red_tagged_tree.item(item, tags=('urgent',))
        
        # Configure tags
        self.red_tagged_tree.tag_configure('overdue', background='#ffcdd2')
        self.red_tagged_tree.tag_configure('urgent', background='#ffecb3')
    
    def populate_expiring_report(self):
        """Populate expiring soft goods report"""
        # Clear existing items
        for item in self.expiring_tree.get_children():
            self.expiring_tree.delete(item)
        
        # Update count label
        count = len(self.expiring_data)
        self.expiring_count_label.config(text=f"Found {count} soft goods expiring within 12 months")
        
        # Add items
        for equipment in self.expiring_data:
            first_use_date = equipment.get('first_use_date')
            expiry_date = equipment.get('expiry_date')
            days_remaining = int(equipment.get('days_remaining', 0))
            
            # Priority based on days remaining
            if days_remaining <= 30:
                priority = "HIGH"
            elif days_remaining <= 90:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            values = (
                equipment['equipment_id'],
                equipment['equipment_type'],
                equipment['type_description'],
                format_date(first_use_date),
                format_date(expiry_date),
                str(max(0, days_remaining)),
                priority
            )
            
            item = self.expiring_tree.insert('', 'end', values=values)
            
            # Color code by priority
            if priority == 'HIGH':
                self.expiring_tree.item(item, tags=('high_priority',))
            elif priority == 'MEDIUM':
                self.expiring_tree.item(item, tags=('medium_priority',))
        
        # Configure tags
        self.expiring_tree.tag_configure('high_priority', background='#ffecb3')
        self.expiring_tree.tag_configure('medium_priority', background='#f3e5f5')
    
    def populate_summary_report(self):
        """Populate summary report with critical alerts"""
        # Clear alerts text
        self.alerts_text.config(state='normal')
        self.alerts_text.delete(1.0, tk.END)
        
        alerts = []
        
        # Critical overdue inspections
        critical_overdue = [eq for eq in self.overdue_data 
                           if eq.get('last_inspection_date') is None or 
                           (datetime.now().date() - datetime.strptime(eq.get('last_inspection_date', '1900-01-01'), '%Y-%m-%d').date()).days > 365]
        
        if critical_overdue:
            alerts.append(f"🚨 CRITICAL: {len(critical_overdue)} equipment items have not been inspected in over 1 year")
        
        # Red tagged equipment about to expire
        urgent_red_tagged = [eq for eq in self.red_tagged_data if int(eq.get('days_remaining', 0)) <= 7]
        if urgent_red_tagged:
            alerts.append(f"🔴 URGENT: {len(urgent_red_tagged)} red tagged items must be destroyed within 7 days")
        
        # Overdue red tagged destruction
        overdue_red_tagged = [eq for eq in self.red_tagged_data if int(eq.get('days_remaining', 0)) <= 0]
        if overdue_red_tagged:
            alerts.append(f"❌ OVERDUE: {len(overdue_red_tagged)} red tagged items should have been destroyed already")
        
        # Expiring soft goods
        expiring_soon = [eq for eq in self.expiring_data if int(eq.get('days_remaining', 0)) <= 90]
        if expiring_soon:
            alerts.append(f"⏰ WARNING: {len(expiring_soon)} soft goods expire within 90 days")
        
        # General overdue inspections
        general_overdue = len(self.overdue_data)
        if general_overdue > 0:
            alerts.append(f"🔍 ATTENTION: {general_overdue} equipment items have overdue inspections")
        
        if alerts:
            alert_text = "The following issues require immediate attention:\n\n"
            for i, alert in enumerate(alerts, 1):
                alert_text += f"{i}. {alert}\n\n"
            
            alert_text += "\nRecommended Actions:\n"
            alert_text += "• Schedule immediate inspections for overdue equipment\n"
            alert_text += "• Destroy overdue red tagged equipment immediately\n"
            alert_text += "• Plan replacement for expiring soft goods\n"
            alert_text += "• Review inspection procedures and schedules\n"
        else:
            alert_text = "✅ All Good!\n\nNo critical alerts at this time.\n\n"
            alert_text += "• All equipment inspections are up to date\n"
            alert_text += "• No red tagged equipment requires immediate destruction\n"
            alert_text += "• No soft goods are expiring soon\n"
        
        self.alerts_text.insert(1.0, alert_text)
        self.alerts_text.config(state='disabled')
    
    def export_reports(self):
        """Export all reports to CSV files"""
        try:
            # Ask for directory
            directory = filedialog.askdirectory(
                title="Select directory to save reports"
            )
            
            if not directory:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export overdue inspections
            if self.overdue_data:
                overdue_filename = f"{directory}/overdue_inspections_{timestamp}.csv"
                self.export_data_to_csv(self.overdue_data, overdue_filename, 
                                       ['equipment_id', 'equipment_type', 'type_description', 
                                        'last_inspection_date', 'next_due_date'])
            
            # Export red tagged equipment
            if self.red_tagged_data:
                red_tagged_filename = f"{directory}/red_tagged_equipment_{timestamp}.csv"
                self.export_data_to_csv(self.red_tagged_data, red_tagged_filename,
                                       ['equipment_id', 'equipment_type', 'type_description',
                                        'red_tag_date', 'destroy_by_date', 'days_remaining'])
            
            # Export expiring equipment
            if self.expiring_data:
                expiring_filename = f"{directory}/expiring_equipment_{timestamp}.csv"
                self.export_data_to_csv(self.expiring_data, expiring_filename,
                                       ['equipment_id', 'equipment_type', 'type_description',
                                        'first_use_date', 'expiry_date', 'days_remaining'])
            
            messagebox.showinfo("Success", f"Reports exported successfully to {directory}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export reports: {str(e)}")
    
    def export_data_to_csv(self, data: List[Dict], filename: str, headers: List[str]):
        """Export data to CSV file"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for row in data:
                # Filter row to only include specified headers
                filtered_row = {key: row.get(key, '') for key in headers}
                writer.writerow(filtered_row)
