#!/usr/bin/env python3
"""
Equipment Inventory Management System
Main application entry point
"""

import tkinter as tk
from tkinter import messagebox
import os
import sys
from database import DatabaseManager
from ui.main_window import MainWindow

class EquipmentInventoryApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Equipment Inventory Management System")
        self.root.geometry("1200x800")
        
        # Initialize database
        try:
            self.db_manager = DatabaseManager()
            self.db_manager.initialize_database()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {str(e)}")
            sys.exit(1)
        
        # Create main window
        self.main_window = MainWindow(self.root, self.db_manager)
        
        # Center window on screen
        self.center_window()
        
    def center_window(self):
        """Center the main window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            messagebox.showerror("Application Error", f"An unexpected error occurred: {str(e)}")
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of application"""
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
        except:
            pass
        self.root.quit()

if __name__ == "__main__":
    app = EquipmentInventoryApp()
    app.run()
