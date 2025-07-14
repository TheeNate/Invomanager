"""
Equipment form window for adding/editing equipment
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import Optional, Dict, Callable
from database import DatabaseManager
from utils.validators import FormValidator
from utils.helpers import parse_date, format_date

class EquipmentFormWindow:
    def __init__(self, parent: tk.Tk, db_manager: DatabaseManager, 
                 equipment: Optional[Dict] = None, callback: Optional[Callable] = None):
        self.parent = parent
        self.db_manager = db_manager
        self.equipment = equipment
        self.callback = callback
        self.is_edit_mode = equipment is not None
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Edit Equipment" if self.is_edit_mode else "Add Equipment")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center window
        self.center_window()
        
        # Create form
        self.create_widgets()
        self.setup_layout()
        
        # Load data if editing
        if self.is_edit_mode:
            self.load_equipment_data()
        
        # Load equipment types
        self.load_equipment_types()
    
    def center_window(self):
        """Center the window on parent"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create form widgets"""
        
        # Main frame
        self.main_frame = ttk.Frame(self.window)
        
        # Form frame
        self.form_frame = ttk.LabelFrame(self.main_frame, text="Equipment Information")
        
        # Equipment ID (read-only in edit mode)
        ttk.Label(self.form_frame, text="Equipment ID:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        if self.is_edit_mode:
            self.equipment_id_var = tk.StringVar()
            ttk.Label(self.form_frame, textvariable=self.equipment_id_var, 
                     font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=1, sticky='w', padx=5, pady=5)
        else:
            ttk.Label(self.form_frame, text="(Auto-generated)", 
                     style='TLabel').grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        # Equipment Type
        ttk.Label(self.form_frame, text="Equipment Type:*").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(
            self.form_frame, textvariable=self.type_var, 
            state='readonly' if self.is_edit_mode else 'readonly',
            width=30
        )
        self.type_combo.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        # Serial Number
        ttk.Label(self.form_frame, text="Serial Number:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.serial_var = tk.StringVar()
        self.serial_entry = ttk.Entry(self.form_frame, textvariable=self.serial_var, width=30)
        self.serial_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        # Purchase Date
        ttk.Label(self.form_frame, text="Purchase Date:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.purchase_date_var = tk.StringVar()
        self.purchase_date_entry = ttk.Entry(self.form_frame, textvariable=self.purchase_date_var, width=30)
        self.purchase_date_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        ttk.Label(self.form_frame, text="(YYYY-MM-DD format)", 
                 font=('TkDefaultFont', 8)).grid(row=3, column=2, sticky='w', padx=5, pady=5)
        
        # First Use Date
        ttk.Label(self.form_frame, text="First Use Date:").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        self.first_use_date_var = tk.StringVar()
        self.first_use_date_entry = ttk.Entry(self.form_frame, textvariable=self.first_use_date_var, width=30)
        self.first_use_date_entry.grid(row=4, column=1, sticky='w', padx=5, pady=5)
        ttk.Label(self.form_frame, text="(YYYY-MM-DD format)", 
                 font=('TkDefaultFont', 8)).grid(row=4, column=2, sticky='w', padx=5, pady=5)
        
        # Status (edit mode only)
        if self.is_edit_mode:
            ttk.Label(self.form_frame, text="Status:").grid(row=5, column=0, sticky='w', padx=5, pady=5)
            self.status_var = tk.StringVar()
            self.status_combo = ttk.Combobox(
                self.form_frame, textvariable=self.status_var,
                values=['ACTIVE', 'RED_TAGGED', 'DESTROYED'],
                state='readonly', width=30
            )
            self.status_combo.grid(row=5, column=1, sticky='w', padx=5, pady=5)
        
        # Required fields note
        ttk.Label(self.form_frame, text="* Required fields", 
                 font=('TkDefaultFont', 8)).grid(row=6, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.main_frame)
        
        self.btn_save = ttk.Button(
            self.buttons_frame, text="Update" if self.is_edit_mode else "Add Equipment", 
            command=self.save_equipment
        )
        self.btn_cancel = ttk.Button(
            self.buttons_frame, text="Cancel", 
            command=self.window.destroy
        )
    
    def setup_layout(self):
        """Layout the widgets"""
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.form_frame.pack(fill='x', pady=(0, 10))
        
        self.buttons_frame.pack(fill='x')
        self.btn_cancel.pack(side='right')
        self.btn_save.pack(side='right', padx=(0, 10))
    
    def load_equipment_types(self):
        """Load equipment types into combobox"""
        try:
            types = self.db_manager.get_equipment_types()
            type_values = [f"{t['type_code']} - {t['description']}" for t in types]
            self.type_combo['values'] = type_values
            
            if not self.is_edit_mode and type_values:
                self.type_combo.set(type_values[0])
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment types: {str(e)}")
    
    def load_equipment_data(self):
        """Load existing equipment data into form"""
        if not self.equipment:
            return
        
        self.equipment_id_var.set(self.equipment['equipment_id'])
        
        # Set type
        type_text = f"{self.equipment['equipment_type']} - {self.equipment['type_description']}"
        self.type_var.set(type_text)
        
        # Set other fields
        self.serial_var.set(self.equipment['serial_number'] or '')
        self.purchase_date_var.set(format_date(self.equipment['purchase_date']) or '')
        self.first_use_date_var.set(format_date(self.equipment['first_use_date']) or '')
        
        if hasattr(self, 'status_var'):
            self.status_var.set(self.equipment['status'])
    
    def validate_form(self) -> bool:
        """Validate form data"""
        # Get values
        equipment_type = self.type_var.get().split(' - ')[0] if self.type_var.get() else ''
        serial_number = self.serial_var.get().strip()
        purchase_date = parse_date(self.purchase_date_var.get().strip())
        first_use_date = parse_date(self.first_use_date_var.get().strip())
        
        # Validate
        errors = FormValidator.validate_equipment_form(
            equipment_type, serial_number, purchase_date, first_use_date
        )
        
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        
        return True
    
    def save_equipment(self):
        """Save equipment data"""
        if not self.validate_form():
            return
        
        try:
            # Get form data
            equipment_type = self.type_var.get().split(' - ')[0]
            serial_number = self.serial_var.get().strip() or None
            purchase_date = parse_date(self.purchase_date_var.get().strip())
            first_use_date = parse_date(self.first_use_date_var.get().strip())
            
            if self.is_edit_mode:
                # Update existing equipment
                # Note: In a full implementation, you'd need update methods in DatabaseManager
                # For now, we'll show a message about limitations
                
                # Check if status changed
                old_status = self.equipment['status']
                new_status = self.status_var.get()
                
                if old_status != new_status:
                    # Update status
                    success = self.db_manager.update_equipment_status(
                        self.equipment['equipment_id'], new_status
                    )
                    if not success:
                        messagebox.showerror("Error", "Failed to update equipment status")
                        return
                
                messagebox.showinfo("Info", 
                    "Equipment updated successfully!\n\n" +
                    "Note: Serial number and date updates are not yet implemented in this version.")
            
            else:
                # Add new equipment
                equipment_id = self.db_manager.add_equipment(
                    equipment_type, serial_number, purchase_date, first_use_date
                )
                messagebox.showinfo("Success", f"Equipment added successfully!\nID: {equipment_id}")
            
            # Refresh parent and close
            if self.callback:
                self.callback()
            
            self.window.destroy()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save equipment: {str(e)}")
