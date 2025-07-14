"""
Main window for Equipment Inventory Management System
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from typing import Optional, Dict, List
from database import DatabaseManager
from ui.equipment_form import EquipmentFormWindow
from ui.inspection_form import InspectionFormWindow
from ui.equipment_types_form import EquipmentTypesWindow
from ui.reports_window import ReportsWindow
from utils.helpers import format_date, get_status_color, truncate_string

class MainWindow:
    def __init__(self, root: tk.Tk, db_manager: DatabaseManager):
        self.root = root
        self.db_manager = db_manager
        
        # Configure main window
        self.root.title("Equipment Inventory Management System")
        
        # Initialize variables
        self.equipment_list = []
        self.filtered_equipment = []
        self.selected_equipment_id = None
        
        # Create UI
        self.create_widgets()
        self.setup_layout()
        
        # Load initial data
        self.refresh_equipment_list()
        self.refresh_equipment_types()
    
    def create_widgets(self):
        """Create all UI widgets"""
        
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        
        # Toolbar
        self.toolbar_frame = ttk.Frame(self.main_frame)
        
        # Equipment management buttons
        self.btn_add_equipment = ttk.Button(
            self.toolbar_frame, text="Add Equipment", 
            command=self.add_equipment
        )
        self.btn_edit_equipment = ttk.Button(
            self.toolbar_frame, text="Edit Equipment", 
            command=self.edit_equipment, state='disabled'
        )
        self.btn_add_inspection = ttk.Button(
            self.toolbar_frame, text="Add Inspection", 
            command=self.add_inspection, state='disabled'
        )
        
        # Separator
        ttk.Separator(self.toolbar_frame, orient='vertical').pack(side='left', fill='y', padx=5)
        
        # Management buttons
        self.btn_equipment_types = ttk.Button(
            self.toolbar_frame, text="Equipment Types", 
            command=self.manage_equipment_types
        )
        self.btn_reports = ttk.Button(
            self.toolbar_frame, text="Reports", 
            command=self.show_reports
        )
        
        # Separator
        ttk.Separator(self.toolbar_frame, orient='vertical').pack(side='left', fill='y', padx=5)
        
        # Export button
        self.btn_export = ttk.Button(
            self.toolbar_frame, text="Export CSV", 
            command=self.export_data
        )
        
        # Filter frame
        self.filter_frame = ttk.LabelFrame(self.main_frame, text="Filters")
        
        # Status filter
        ttk.Label(self.filter_frame, text="Status:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.status_filter = ttk.Combobox(
            self.filter_frame, values=['All', 'ACTIVE', 'RED_TAGGED', 'DESTROYED'],
            state='readonly', width=12
        )
        self.status_filter.set('All')
        self.status_filter.bind('<<ComboboxSelected>>', self.apply_filters)
        
        # Type filter
        ttk.Label(self.filter_frame, text="Type:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.type_filter = ttk.Combobox(self.filter_frame, state='readonly', width=12)
        self.type_filter.bind('<<ComboboxSelected>>', self.apply_filters)
        
        # Search
        ttk.Label(self.filter_frame, text="Search:").grid(row=0, column=4, padx=5, pady=5, sticky='w')
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.apply_filters)
        self.search_entry = ttk.Entry(self.filter_frame, textvariable=self.search_var, width=20)
        
        # Clear filters button
        self.btn_clear_filters = ttk.Button(
            self.filter_frame, text="Clear", 
            command=self.clear_filters
        )
        
        # Equipment list frame
        self.list_frame = ttk.Frame(self.main_frame)
        
        # Equipment treeview
        columns = ('ID', 'Type', 'Description', 'Serial', 'Status', 'Last Inspection', 'Next Due')
        self.equipment_tree = ttk.Treeview(
            self.list_frame, columns=columns, show='headings', height=15
        )
        
        # Configure columns
        self.equipment_tree.heading('ID', text='Equipment ID')
        self.equipment_tree.heading('Type', text='Type')
        self.equipment_tree.heading('Description', text='Description')
        self.equipment_tree.heading('Serial', text='Serial Number')
        self.equipment_tree.heading('Status', text='Status')
        self.equipment_tree.heading('Last Inspection', text='Last Inspection')
        self.equipment_tree.heading('Next Due', text='Next Due')
        
        self.equipment_tree.column('ID', width=100)
        self.equipment_tree.column('Type', width=60)
        self.equipment_tree.column('Description', width=150)
        self.equipment_tree.column('Serial', width=120)
        self.equipment_tree.column('Status', width=100)
        self.equipment_tree.column('Last Inspection', width=120)
        self.equipment_tree.column('Next Due', width=120)
        
        # Bind events
        self.equipment_tree.bind('<<TreeviewSelect>>', self.on_equipment_select)
        self.equipment_tree.bind('<Double-1>', self.view_equipment_details)
        
        # Scrollbars
        self.tree_scroll_y = ttk.Scrollbar(self.list_frame, orient='vertical', command=self.equipment_tree.yview)
        self.equipment_tree.configure(yscrollcommand=self.tree_scroll_y.set)
        
        self.tree_scroll_x = ttk.Scrollbar(self.list_frame, orient='horizontal', command=self.equipment_tree.xview)
        self.equipment_tree.configure(xscrollcommand=self.tree_scroll_x.set)
        
        # Status bar
        self.status_bar = ttk.Label(
            self.main_frame, text="Ready", 
            relief='sunken', anchor='w'
        )
    
    def setup_layout(self):
        """Layout all widgets"""
        
        # Main frame
        self.main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Toolbar
        self.toolbar_frame.pack(fill='x', pady=(0, 5))
        
        # Toolbar buttons
        self.btn_add_equipment.pack(side='left', padx=(0, 5))
        self.btn_edit_equipment.pack(side='left', padx=(0, 5))
        self.btn_add_inspection.pack(side='left', padx=(0, 10))
        self.btn_equipment_types.pack(side='left', padx=(0, 5))
        self.btn_reports.pack(side='left', padx=(0, 10))
        self.btn_export.pack(side='left')
        
        # Filter frame
        self.filter_frame.pack(fill='x', pady=(0, 5))
        
        # Filter widgets
        self.status_filter.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.type_filter.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        self.search_entry.grid(row=0, column=5, padx=5, pady=5, sticky='w')
        self.btn_clear_filters.grid(row=0, column=6, padx=10, pady=5)
        
        # Equipment list
        self.list_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        # Treeview and scrollbars
        self.equipment_tree.grid(row=0, column=0, sticky='nsew')
        self.tree_scroll_y.grid(row=0, column=1, sticky='ns')
        self.tree_scroll_x.grid(row=1, column=0, sticky='ew')
        
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)
        
        # Status bar
        self.status_bar.pack(fill='x')
    
    def refresh_equipment_list(self):
        """Refresh the equipment list from database"""
        try:
            self.equipment_list = self.db_manager.get_equipment_list()
            self.apply_filters()
            self.update_status_bar()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment list: {str(e)}")
    
    def refresh_equipment_types(self):
        """Refresh equipment types for filter dropdown"""
        try:
            types = self.db_manager.get_equipment_types()
            type_values = ['All'] + [f"{t['type_code']} - {t['description']}" for t in types]
            self.type_filter['values'] = type_values
            self.type_filter.set('All')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment types: {str(e)}")
    
    def apply_filters(self, *args):
        """Apply current filters to equipment list"""
        filtered = self.equipment_list.copy()
        
        # Status filter
        status_filter = self.status_filter.get()
        if status_filter != 'All':
            filtered = [eq for eq in filtered if eq['status'] == status_filter]
        
        # Type filter
        type_filter = self.type_filter.get()
        if type_filter != 'All' and type_filter:
            type_code = type_filter.split(' - ')[0]
            filtered = [eq for eq in filtered if eq['equipment_type'] == type_code]
        
        # Search filter
        search_term = self.search_var.get().strip().lower()
        if search_term:
            filtered = [
                eq for eq in filtered
                if search_term in eq['equipment_id'].lower() or
                   search_term in (eq['serial_number'] or '').lower() or
                   search_term in (eq['type_description'] or '').lower()
            ]
        
        self.filtered_equipment = filtered
        self.populate_equipment_tree()
    
    def populate_equipment_tree(self):
        """Populate treeview with filtered equipment"""
        # Clear existing items
        for item in self.equipment_tree.get_children():
            self.equipment_tree.delete(item)
        
        # Add equipment items
        for equipment in self.filtered_equipment:
            # Get last inspection info
            try:
                last_inspection = self.db_manager.get_last_inspection(equipment['equipment_id'])
                if last_inspection:
                    last_inspection_date = format_date(last_inspection['inspection_date'])
                    # Calculate next due date (simplified - using 6 months)
                    from datetime import datetime, timedelta
                    last_date = datetime.strptime(last_inspection_date, '%Y-%m-%d').date()
                    next_due_date = last_date + timedelta(days=180)  # 6 months
                    next_due = format_date(next_due_date)
                else:
                    last_inspection_date = "Never"
                    next_due = "Overdue"
            except:
                last_inspection_date = "Error"
                next_due = "Unknown"
            
            values = (
                equipment['equipment_id'],
                equipment['equipment_type'],
                truncate_string(equipment['type_description'], 20),
                truncate_string(equipment['serial_number'] or '', 15),
                equipment['status'],
                last_inspection_date,
                next_due
            )
            
            item = self.equipment_tree.insert('', 'end', values=values)
            
            # Color code by status
            status = equipment['status']
            if status == 'RED_TAGGED':
                self.equipment_tree.set(item, 'Status', '🔴 RED_TAGGED')
            elif status == 'DESTROYED':
                self.equipment_tree.set(item, 'Status', '❌ DESTROYED')
            elif status == 'ACTIVE':
                self.equipment_tree.set(item, 'Status', '✅ ACTIVE')
        
        self.update_status_bar()
    
    def clear_filters(self):
        """Clear all filters"""
        self.status_filter.set('All')
        self.type_filter.set('All')
        self.search_var.set('')
        self.apply_filters()
    
    def on_equipment_select(self, event):
        """Handle equipment selection"""
        selection = self.equipment_tree.selection()
        if selection:
            item = selection[0]
            equipment_id = self.equipment_tree.item(item, 'values')[0]
            self.selected_equipment_id = equipment_id
            
            # Enable context buttons
            self.btn_edit_equipment.config(state='normal')
            self.btn_add_inspection.config(state='normal')
        else:
            self.selected_equipment_id = None
            self.btn_edit_equipment.config(state='disabled')
            self.btn_add_inspection.config(state='disabled')
    
    def view_equipment_details(self, event):
        """View detailed equipment information"""
        if self.selected_equipment_id:
            self.show_equipment_details(self.selected_equipment_id)
    
    def show_equipment_details(self, equipment_id: str):
        """Show equipment details in popup window"""
        try:
            equipment = self.db_manager.get_equipment_by_id(equipment_id)
            if not equipment:
                messagebox.showerror("Error", "Equipment not found")
                return
            
            inspections = self.db_manager.get_equipment_inspections(equipment_id)
            
            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Equipment Details - {equipment_id}")
            details_window.geometry("600x500")
            details_window.transient(self.root)
            details_window.grab_set()
            
            # Equipment info frame
            info_frame = ttk.LabelFrame(details_window, text="Equipment Information")
            info_frame.pack(fill='x', padx=10, pady=5)
            
            # Equipment details
            details = [
                ("Equipment ID:", equipment['equipment_id']),
                ("Type:", f"{equipment['equipment_type']} - {equipment['type_description']}"),
                ("Serial Number:", equipment['serial_number'] or 'Not specified'),
                ("Status:", equipment['status']),
                ("Purchase Date:", format_date(equipment['purchase_date']) or 'Not specified'),
                ("First Use Date:", format_date(equipment['first_use_date']) or 'Not specified'),
                ("Is Soft Goods:", "Yes" if equipment['is_soft_goods'] else "No")
            ]
            
            for i, (label, value) in enumerate(details):
                ttk.Label(info_frame, text=label, font=('TkDefaultFont', 9, 'bold')).grid(
                    row=i, column=0, sticky='w', padx=5, pady=2
                )
                ttk.Label(info_frame, text=str(value)).grid(
                    row=i, column=1, sticky='w', padx=10, pady=2
                )
            
            # Inspections frame
            insp_frame = ttk.LabelFrame(details_window, text="Inspection History")
            insp_frame.pack(fill='both', expand=True, padx=10, pady=5)
            
            # Inspections treeview
            insp_columns = ('Date', 'Result', 'Inspector', 'Notes')
            insp_tree = ttk.Treeview(insp_frame, columns=insp_columns, show='headings', height=10)
            
            for col in insp_columns:
                insp_tree.heading(col, text=col)
                insp_tree.column(col, width=120)
            
            # Add inspections
            for inspection in inspections:
                values = (
                    format_date(inspection['inspection_date']),
                    inspection['result'],
                    inspection['inspector_name'],
                    truncate_string(inspection['notes'] or '', 30)
                )
                item = insp_tree.insert('', 'end', values=values)
                
                # Color code by result
                if inspection['result'] == 'FAIL':
                    insp_tree.set(item, 'Result', '❌ FAIL')
                else:
                    insp_tree.set(item, 'Result', '✅ PASS')
            
            insp_tree.pack(fill='both', expand=True, padx=5, pady=5)
            
            # Buttons frame
            btn_frame = ttk.Frame(details_window)
            btn_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Button(btn_frame, text="Close", command=details_window.destroy).pack(side='right')
            
            if equipment['status'] == 'ACTIVE':
                ttk.Button(
                    btn_frame, text="Add Inspection", 
                    command=lambda: self.add_inspection_for_equipment(equipment_id, details_window)
                ).pack(side='right', padx=(0, 5))
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment details: {str(e)}")
    
    def add_equipment(self):
        """Open add equipment form"""
        form = EquipmentFormWindow(self.root, self.db_manager, callback=self.refresh_equipment_list)
    
    def edit_equipment(self):
        """Open edit equipment form"""
        if not self.selected_equipment_id:
            return
        
        equipment = self.db_manager.get_equipment_by_id(self.selected_equipment_id)
        if equipment:
            form = EquipmentFormWindow(
                self.root, self.db_manager, 
                equipment=equipment, 
                callback=self.refresh_equipment_list
            )
    
    def add_inspection(self):
        """Open add inspection form"""
        if not self.selected_equipment_id:
            return
        
        form = InspectionFormWindow(
            self.root, self.db_manager, 
            equipment_id=self.selected_equipment_id,
            callback=self.refresh_equipment_list
        )
    
    def add_inspection_for_equipment(self, equipment_id: str, parent_window):
        """Add inspection for specific equipment from details window"""
        parent_window.destroy()
        form = InspectionFormWindow(
            self.root, self.db_manager, 
            equipment_id=equipment_id,
            callback=self.refresh_equipment_list
        )
    
    def manage_equipment_types(self):
        """Open equipment types management window"""
        types_window = EquipmentTypesWindow(
            self.root, self.db_manager,
            callback=self.refresh_equipment_types
        )
    
    def show_reports(self):
        """Open reports window"""
        reports_window = ReportsWindow(self.root, self.db_manager)
    
    def export_data(self):
        """Export equipment data to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export Equipment Data",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                success = self.db_manager.export_to_csv("equipment_summary", filename)
                if success:
                    messagebox.showinfo("Success", f"Data exported to {filename}")
                else:
                    messagebox.showerror("Error", "Failed to export data")
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")
    
    def update_status_bar(self):
        """Update status bar with current information"""
        total = len(self.equipment_list)
        filtered = len(self.filtered_equipment)
        
        if filtered == total:
            status_text = f"Showing {total} equipment items"
        else:
            status_text = f"Showing {filtered} of {total} equipment items"
        
        # Add counts by status
        if self.equipment_list:
            active_count = len([eq for eq in self.equipment_list if eq['status'] == 'ACTIVE'])
            red_tagged_count = len([eq for eq in self.equipment_list if eq['status'] == 'RED_TAGGED'])
            destroyed_count = len([eq for eq in self.equipment_list if eq['status'] == 'DESTROYED'])
            
            status_text += f" | Active: {active_count}, Red Tagged: {red_tagged_count}, Destroyed: {destroyed_count}"
        
        self.status_bar.config(text=status_text)
