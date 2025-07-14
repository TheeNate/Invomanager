"""
Inspection form window for recording equipment inspections
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from typing import Optional, Callable
from database import DatabaseManager
from utils.validators import FormValidator
from utils.helpers import parse_date, format_date

class InspectionFormWindow:
    def __init__(self, parent: tk.Tk, db_manager: DatabaseManager, 
                 equipment_id: Optional[str] = None, callback: Optional[Callable] = None):
        self.parent = parent
        self.db_manager = db_manager
        self.equipment_id = equipment_id
        self.callback = callback
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Record Inspection")
        self.window.geometry("500x450")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center window
        self.center_window()
        
        # Create form
        self.create_widgets()
        self.setup_layout()
        
        # Load data
        self.load_equipment_list()
        
        # Set default values
        self.set_defaults()
    
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
        
        # Equipment info frame
        self.equipment_frame = ttk.LabelFrame(self.main_frame, text="Equipment Information")
        
        # Equipment selection
        ttk.Label(self.equipment_frame, text="Equipment:*").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.equipment_var = tk.StringVar()
        self.equipment_combo = ttk.Combobox(
            self.equipment_frame, textvariable=self.equipment_var,
            state='readonly', width=40
        )
        self.equipment_combo.grid(row=0, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.equipment_combo.bind('<<ComboboxSelected>>', self.on_equipment_select)
        
        # Equipment details display
        self.equipment_details_frame = ttk.Frame(self.equipment_frame)
        self.equipment_details_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        self.details_text = tk.Text(
            self.equipment_details_frame, height=4, width=50,
            state='disabled', wrap='word'
        )
        self.details_text.pack(fill='x')
        
        # Inspection form frame
        self.inspection_frame = ttk.LabelFrame(self.main_frame, text="Inspection Details")
        
        # Inspection Date
        ttk.Label(self.inspection_frame, text="Inspection Date:*").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.inspection_date_var = tk.StringVar()
        self.inspection_date_entry = ttk.Entry(self.inspection_frame, textvariable=self.inspection_date_var, width=20)
        self.inspection_date_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        # Today button
        self.btn_today = ttk.Button(
            self.inspection_frame, text="Today", 
            command=self.set_today_date
        )
        self.btn_today.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(self.inspection_frame, text="(YYYY-MM-DD format)", 
                 font=('TkDefaultFont', 8)).grid(row=0, column=3, sticky='w', padx=5, pady=5)
        
        # Inspection Result
        ttk.Label(self.inspection_frame, text="Result:*").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.result_var = tk.StringVar()
        self.result_frame = ttk.Frame(self.inspection_frame)
        self.result_frame.grid(row=1, column=1, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.pass_radio = ttk.Radiobutton(
            self.result_frame, text="✅ PASS", 
            variable=self.result_var, value="PASS"
        )
        self.pass_radio.pack(side='left', padx=(0, 20))
        
        self.fail_radio = ttk.Radiobutton(
            self.result_frame, text="❌ FAIL", 
            variable=self.result_var, value="FAIL"
        )
        self.fail_radio.pack(side='left')
        
        # Failure warning
        self.fail_warning = ttk.Label(
            self.inspection_frame, 
            text="⚠️ Failed inspections will automatically RED TAG the equipment",
            foreground='red', font=('TkDefaultFont', 8)
        )
        self.fail_warning.grid(row=2, column=1, columnspan=3, sticky='w', padx=5, pady=(0, 5))
        self.fail_warning.grid_remove()  # Hidden by default
        
        # Bind result change to show/hide warning
        self.result_var.trace('w', self.on_result_change)
        
        # Inspector Name
        ttk.Label(self.inspection_frame, text="Inspector Name:*").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.inspector_var = tk.StringVar()
        self.inspector_entry = ttk.Entry(self.inspection_frame, textvariable=self.inspector_var, width=30)
        self.inspector_entry.grid(row=3, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        
        # Notes
        ttk.Label(self.inspection_frame, text="Notes:").grid(row=4, column=0, sticky='nw', padx=5, pady=5)
        
        self.notes_frame = ttk.Frame(self.inspection_frame)
        self.notes_frame.grid(row=4, column=1, columnspan=3, sticky='ew', padx=5, pady=5)
        
        self.notes_text = tk.Text(self.notes_frame, height=5, width=40, wrap='word')
        self.notes_scroll = ttk.Scrollbar(self.notes_frame, orient='vertical', command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=self.notes_scroll.set)
        
        self.notes_text.pack(side='left', fill='both', expand=True)
        self.notes_scroll.pack(side='right', fill='y')
        
        # Required fields note
        ttk.Label(self.inspection_frame, text="* Required fields", 
                 font=('TkDefaultFont', 8)).grid(row=5, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.main_frame)
        
        self.btn_save = ttk.Button(
            self.buttons_frame, text="Record Inspection", 
            command=self.save_inspection
        )
        self.btn_cancel = ttk.Button(
            self.buttons_frame, text="Cancel", 
            command=self.window.destroy
        )
    
    def setup_layout(self):
        """Layout the widgets"""
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.equipment_frame.pack(fill='x', pady=(0, 10))
        self.inspection_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Configure grid weights
        self.inspection_frame.grid_columnconfigure(1, weight=1)
        self.notes_frame.grid_columnconfigure(0, weight=1)
        
        self.buttons_frame.pack(fill='x')
        self.btn_cancel.pack(side='right')
        self.btn_save.pack(side='right', padx=(0, 10))
    
    def load_equipment_list(self):
        """Load equipment list for selection"""
        try:
            # Get only active equipment
            equipment_list = self.db_manager.get_equipment_list(status_filter='ACTIVE')
            
            if not equipment_list:
                messagebox.showwarning("Warning", "No active equipment found")
                self.window.destroy()
                return
            
            # Create equipment options
            equipment_options = []
            for eq in equipment_list:
                option = f"{eq['equipment_id']} - {eq['type_description']}"
                if eq['serial_number']:
                    option += f" (S/N: {eq['serial_number']})"
                equipment_options.append(option)
            
            self.equipment_combo['values'] = equipment_options
            self.equipment_list = equipment_list  # Store for reference
            
            # Pre-select if equipment_id provided
            if self.equipment_id:
                for i, eq in enumerate(equipment_list):
                    if eq['equipment_id'] == self.equipment_id:
                        self.equipment_combo.current(i)
                        self.on_equipment_select()
                        break
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment list: {str(e)}")
            self.window.destroy()
    
    def on_equipment_select(self, event=None):
        """Handle equipment selection"""
        selection = self.equipment_combo.current()
        if selection >= 0:
            equipment = self.equipment_list[selection]
            self.show_equipment_details(equipment)
    
    def show_equipment_details(self, equipment: dict):
        """Display equipment details"""
        try:
            # Get last inspection
            last_inspection = self.db_manager.get_last_inspection(equipment['equipment_id'])
            
            details = f"Equipment ID: {equipment['equipment_id']}\n"
            details += f"Type: {equipment['equipment_type']} - {equipment['type_description']}\n"
            details += f"Serial Number: {equipment['serial_number'] or 'Not specified'}\n"
            
            if last_inspection:
                details += f"Last Inspection: {format_date(last_inspection['inspection_date'])} ({last_inspection['result']})"
            else:
                details += "Last Inspection: Never inspected"
            
            self.details_text.config(state='normal')
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, details)
            self.details_text.config(state='disabled')
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment details: {str(e)}")
    
    def set_defaults(self):
        """Set default form values"""
        # Set today's date
        self.set_today_date()
        
        # Set default result to PASS
        self.result_var.set("PASS")
    
    def set_today_date(self):
        """Set inspection date to today"""
        today = date.today()
        self.inspection_date_var.set(format_date(today))
    
    def on_result_change(self, *args):
        """Handle inspection result change"""
        if self.result_var.get() == "FAIL":
            self.fail_warning.grid()
        else:
            self.fail_warning.grid_remove()
    
    def validate_form(self) -> bool:
        """Validate form data"""
        # Check equipment selection
        if self.equipment_combo.current() < 0:
            messagebox.showerror("Validation Error", "Please select equipment")
            return False
        
        # Get values
        equipment_id = self.equipment_list[self.equipment_combo.current()]['equipment_id']
        inspection_date = parse_date(self.inspection_date_var.get().strip())
        result = self.result_var.get()
        inspector_name = self.inspector_var.get().strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        
        # Validate using form validator
        errors = FormValidator.validate_inspection_form(
            equipment_id, inspection_date, result, inspector_name, notes
        )
        
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        
        # Additional validation - don't allow future dates
        if inspection_date and inspection_date > date.today():
            messagebox.showerror("Validation Error", "Inspection date cannot be in the future")
            return False
        
        return True
    
    def save_inspection(self):
        """Save inspection record"""
        if not self.validate_form():
            return
        
        try:
            # Confirm if FAIL result
            result = self.result_var.get()
            if result == "FAIL":
                confirm = messagebox.askyesno(
                    "Confirm Failed Inspection",
                    "This equipment failed inspection and will be automatically RED TAGGED.\n\n" +
                    "Are you sure you want to continue?"
                )
                if not confirm:
                    return
            
            # Get form data
            equipment = self.equipment_list[self.equipment_combo.current()]
            equipment_id = equipment['equipment_id']
            inspection_date = parse_date(self.inspection_date_var.get().strip())
            inspector_name = self.inspector_var.get().strip()
            notes = self.notes_text.get(1.0, tk.END).strip() or None
            
            # Save inspection
            inspection_id = self.db_manager.add_inspection(
                equipment_id, inspection_date, result, inspector_name, notes
            )
            
            if result == "FAIL":
                messagebox.showinfo(
                    "Inspection Recorded", 
                    f"Inspection recorded successfully!\n\n" +
                    f"Equipment {equipment_id} has been RED TAGGED due to failed inspection.\n" +
                    f"It must be destroyed within 30 days."
                )
            else:
                messagebox.showinfo(
                    "Inspection Recorded", 
                    f"Inspection recorded successfully!\n\n" +
                    f"Equipment {equipment_id} passed inspection."
                )
            
            # Refresh parent and close
            if self.callback:
                self.callback()
            
            self.window.destroy()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save inspection: {str(e)}")
