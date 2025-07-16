"""The UI form help text has been updated to allow type codes of 1-4 letters instead of restricting to single letters only."""
"""
Equipment types management window
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, List
from database import DatabaseManager
from utils.validators import FormValidator
from utils.helpers import safe_int

class EquipmentTypesWindow:
    def __init__(self, parent: tk.Tk, db_manager: DatabaseManager, 
                 callback: Optional[Callable] = None):
        self.parent = parent
        self.db_manager = db_manager
        self.callback = callback

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Equipment Types Management")
        self.window.geometry("800x600")
        self.window.transient(parent)
        self.window.grab_set()

        # Center window
        self.center_window()

        # Initialize data
        self.equipment_types = []
        self.selected_type = None

        # Create UI
        self.create_widgets()
        self.setup_layout()

        # Load data
        self.refresh_types_list()

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

        # Title
        title_label = ttk.Label(
            self.main_frame, text="Equipment Types Management",
            font=('TkDefaultFont', 12, 'bold')
        )

        # Left panel - Types list
        self.left_panel = ttk.LabelFrame(self.main_frame, text="Equipment Types")

        # Types treeview
        columns = ('Code', 'Description', 'Type', 'Lifespan', 'Interval', 'Status')
        self.types_tree = ttk.Treeview(
            self.left_panel, columns=columns, show='headings', height=15
        )

        # Configure columns
        self.types_tree.heading('Code', text='Code')
        self.types_tree.heading('Description', text='Description')
        self.types_tree.heading('Type', text='Type')
        self.types_tree.heading('Lifespan', text='Lifespan (Years)')
        self.types_tree.heading('Interval', text='Inspection (Months)')
        self.types_tree.heading('Status', text='Status')

        self.types_tree.column('Code', width=60)
        self.types_tree.column('Description', width=150)
        self.types_tree.column('Type', width=80)
        self.types_tree.column('Lifespan', width=100)
        self.types_tree.column('Interval', width=120)
        self.types_tree.column('Status', width=80)

        # Bind events
        self.types_tree.bind('<<TreeviewSelect>>', self.on_type_select)

        # Scrollbar for types list
        self.types_scroll = ttk.Scrollbar(self.left_panel, orient='vertical', command=self.types_tree.yview)
        self.types_tree.configure(yscrollcommand=self.types_scroll.set)

        # Right panel - Form
        self.right_panel = ttk.LabelFrame(self.main_frame, text="Type Details")

        # Form frame
        self.form_frame = ttk.Frame(self.right_panel)

        # Type Code
        ttk.Label(self.form_frame, text="Type Code:*").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.type_code_var = tk.StringVar()
        self.type_code_entry = ttk.Entry(self.form_frame, textvariable=self.type_code_var, width=10)
        self.type_code_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        ttk.Label(self.form_frame, text="(1-4 letters)", 
                 font=('TkDefaultFont', 8)).grid(row=0, column=2, sticky='w', padx=5, pady=5)

        # Description
        ttk.Label(self.form_frame, text="Description:*").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.description_var = tk.StringVar()
        self.description_entry = ttk.Entry(self.form_frame, textvariable=self.description_var, width=30)
        self.description_entry.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        # Soft Goods checkbox
        self.is_soft_goods_var = tk.BooleanVar()
        self.soft_goods_check = ttk.Checkbutton(
            self.form_frame, text="Soft Goods (has expiration)", 
            variable=self.is_soft_goods_var,
            command=self.on_soft_goods_change
        )
        self.soft_goods_check.grid(row=2, column=0, columnspan=3, sticky='w', padx=5, pady=5)

        # Lifespan Years
        ttk.Label(self.form_frame, text="Lifespan (Years):").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.lifespan_var = tk.StringVar()
        self.lifespan_entry = ttk.Entry(self.form_frame, textvariable=self.lifespan_var, width=10)
        self.lifespan_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        self.lifespan_note = ttk.Label(self.form_frame, text="(Required for soft goods)", 
                                      font=('TkDefaultFont', 8))
        self.lifespan_note.grid(row=3, column=2, sticky='w', padx=5, pady=5)

        # Inspection Interval
        ttk.Label(self.form_frame, text="Inspection Interval (Months):*").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        self.interval_var = tk.StringVar()
        self.interval_var.set("6")  # Default
        self.interval_entry = ttk.Entry(self.form_frame, textvariable=self.interval_var, width=10)
        self.interval_entry.grid(row=4, column=1, sticky='w', padx=5, pady=5)

        # Required fields note
        ttk.Label(self.form_frame, text="* Required fields", 
                 font=('TkDefaultFont', 8)).grid(row=5, column=0, columnspan=3, sticky='w', padx=5, pady=10)

        # Buttons frame
        self.buttons_frame = ttk.Frame(self.right_panel)

        self.btn_new = ttk.Button(self.buttons_frame, text="New", command=self.new_type)
        self.btn_save = ttk.Button(self.buttons_frame, text="Save", command=self.save_type)
        self.btn_deactivate = ttk.Button(
            self.buttons_frame, text="Deactivate", 
            command=self.deactivate_type, state='disabled'
        )

        # Bottom buttons
        self.bottom_frame = ttk.Frame(self.main_frame)
        self.btn_close = ttk.Button(self.bottom_frame, text="Close", command=self.close_window)

        # Store references
        self.widgets = {
            'title_label': title_label,
        }

    def setup_layout(self):
        """Layout all widgets"""
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Title
        self.widgets['title_label'].pack(pady=(0, 10))

        # Main content - left and right panels
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill='both', expand=True, pady=(0, 10))

        # Left panel
        self.left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))

        # Types tree and scrollbar
        self.types_tree.pack(side='left', fill='both', expand=True)
        self.types_scroll.pack(side='right', fill='y')

        # Right panel
        self.right_panel.pack(side='right', fill='y', padx=(5, 0))

        # Form
        self.form_frame.pack(fill='x', padx=10, pady=10)
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Buttons
        self.buttons_frame.pack(fill='x', padx=10, pady=(0, 10))
        self.btn_new.pack(side='left', padx=(0, 5))
        self.btn_save.pack(side='left', padx=(0, 5))
        self.btn_deactivate.pack(side='left')

        # Bottom buttons
        self.bottom_frame.pack(fill='x')
        self.btn_close.pack(side='right')

        # Initial state
        self.on_soft_goods_change()

    def refresh_types_list(self):
        """Refresh the equipment types list"""
        try:
            self.equipment_types = self.db_manager.get_equipment_types(active_only=False)
            self.populate_types_tree()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load equipment types: {str(e)}")

    def populate_types_tree(self):
        """Populate the types treeview"""
        # Clear existing items
        for item in self.types_tree.get_children():
            self.types_tree.delete(item)

        # Add types
        for type_data in self.equipment_types:
            values = (
                type_data['type_code'],
                type_data['description'],
                'Soft Goods' if type_data['is_soft_goods'] else 'Hardware',
                str(type_data['lifespan_years']) if type_data['lifespan_years'] else 'N/A',
                str(type_data['inspection_interval_months']),
                'Active' if type_data['is_active'] else 'Inactive'
            )

            item = self.types_tree.insert('', 'end', values=values)

            # Color inactive items
            if not type_data['is_active']:
                self.types_tree.item(item, tags=('inactive',))

        # Configure tags
        self.types_tree.tag_configure('inactive', foreground='gray')

    def on_type_select(self, event):
        """Handle type selection"""
        selection = self.types_tree.selection()
        if selection:
            item = selection[0]
            type_code = self.types_tree.item(item, 'values')[0]

            # Find the type data
            self.selected_type = None
            for type_data in self.equipment_types:
                if type_data['type_code'] == type_code:
                    self.selected_type = type_data
                    break

            if self.selected_type:
                self.load_type_into_form(self.selected_type)
                self.btn_deactivate.config(
                    state='normal' if self.selected_type['is_active'] else 'disabled'
                )
        else:
            self.selected_type = None
            self.btn_deactivate.config(state='disabled')

    def load_type_into_form(self, type_data: Dict):
        """Load type data into form"""
        self.type_code_var.set(type_data['type_code'])
        self.description_var.set(type_data['description'])
        self.is_soft_goods_var.set(type_data['is_soft_goods'])
        self.lifespan_var.set(str(type_data['lifespan_years']) if type_data['lifespan_years'] else '')
        self.interval_var.set(str(type_data['inspection_interval_months']))

        # Disable type code editing for existing types
        self.type_code_entry.config(state='disabled')

        self.on_soft_goods_change()

    def clear_form(self):
        """Clear the form"""
        self.type_code_var.set('')
        self.description_var.set('')
        self.is_soft_goods_var.set(False)
        self.lifespan_var.set('')
        self.interval_var.set('6')

        # Enable type code editing for new types
        self.type_code_entry.config(state='normal')

        self.selected_type = None
        self.btn_deactivate.config(state='disabled')

        self.on_soft_goods_change()

    def new_type(self):
        """Start creating new type"""
        self.clear_form()
        self.types_tree.selection_remove(self.types_tree.selection())

    def on_soft_goods_change(self):
        """Handle soft goods checkbox change"""
        is_soft_goods = self.is_soft_goods_var.get()

        if is_soft_goods:
            self.lifespan_entry.config(state='normal')
            self.lifespan_note.config(text="(Required for soft goods)")
        else:
            self.lifespan_entry.config(state='disabled')
            self.lifespan_note.config(text="(Not applicable for hardware)")
            self.lifespan_var.set('')

    def validate_form(self) -> bool:
        """Validate form data"""
        type_code = self.type_code_var.get().strip().upper()
        description = self.description_var.get().strip()
        is_soft_goods = self.is_soft_goods_var.get()
        lifespan_str = self.lifespan_var.get().strip()
        interval_str = self.interval_var.get().strip()

        # Convert values
        lifespan_years = safe_int(lifespan_str) if lifespan_str else None
        inspection_interval = safe_int(interval_str, 6)

        # Validate using form validator
        errors = FormValidator.validate_equipment_type_form(
            type_code, description, is_soft_goods, lifespan_years, inspection_interval
        )

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False

        return True

    def save_type(self):
        """Save equipment type"""
        if not self.validate_form():
            return

        try:
            type_code = self.type_code_var.get().strip().upper()
            description = self.description_var.get().strip()
            is_soft_goods = self.is_soft_goods_var.get()
            lifespan_str = self.lifespan_var.get().strip()
            interval_str = self.interval_var.get().strip()

            lifespan_years = safe_int(lifespan_str) if lifespan_str else None
            inspection_interval = safe_int(interval_str, 6)

            if self.selected_type:
                # Update existing type
                success = self.db_manager.update_equipment_type(
                    type_code, description, is_soft_goods, lifespan_years, inspection_interval
                )
                if success:
                    messagebox.showinfo("Success", "Equipment type updated successfully!")
                else:
                    messagebox.showerror("Error", "Failed to update equipment type")
                    return
            else:
                # Add new type
                success = self.db_manager.add_equipment_type(
                    type_code, description, is_soft_goods, lifespan_years, inspection_interval
                )
                if success:
                    messagebox.showinfo("Success", "Equipment type added successfully!")
                else:
                    messagebox.showerror("Error", "Equipment type code already exists")
                    return

            # Refresh list and callback
            self.refresh_types_list()
            if self.callback:
                self.callback()

            # Clear form
            self.clear_form()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save equipment type: {str(e)}")

    def deactivate_type(self):
        """Deactivate selected equipment type"""
        if not self.selected_type:
            return

        type_code = self.selected_type['type_code']

        # Confirm deactivation
        confirm = messagebox.askyesno(
            "Confirm Deactivation",
            f"Are you sure you want to deactivate equipment type '{type_code}'?\n\n" +
            "This will hide it from new equipment creation but won't affect existing equipment."
        )

        if not confirm:
            return

        try:
            success = self.db_manager.deactivate_equipment_type(type_code)
            if success:
                messagebox.showinfo("Success", f"Equipment type '{type_code}' deactivated successfully!")
                self.refresh_types_list()
                if self.callback:
                    self.callback()
                self.clear_form()
            else:
                messagebox.showerror("Error", "Failed to deactivate equipment type")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to deactivate equipment type: {str(e)}")

    def close_window(self):
        """Close the window"""
        self.window.destroy()