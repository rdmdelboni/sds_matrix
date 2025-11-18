#!/usr/bin/env python3
"""
Test script to demonstrate the integrated progress bar.
Simulates file processing to show progress updates in real-time.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from src.gui.main_app import Application

def simulate_processing():
    """Simulate processing of files to demonstrate progress bar."""
    print("\n📊 Testing Integrated Progress Bar")
    print("=" * 50)

    # Create application
    print("🚀 Creating application...")
    app = Application()

    print("✅ Application created successfully!")
    print("\nℹ️  Progress bar features:")
    print("   - Located below LLM Status label")
    print("   - Shows 7 pixels below status as requested")
    print("   - Displays real-time percentage")
    print("   - Has Cancel button on the right")
    print("\n📝 Simulating file processing...")
    print("-" * 50)

    # Simulate showing the progress bar
    total_files = 50
    app.setup_tab.show_progress(total_files)
    print(f"▶️  Progress bar shown (total files: {total_files})")

    # Simulate processing updates
    for current in range(1, total_files + 1):
        app.setup_tab.update_progress(current, total_files)

        # Simulate processing time
        time.sleep(0.1)

        # Print progress every 10 files
        if current % 10 == 0:
            percentage = (current * 100) // total_files
            print(f"   Processing: {current}/{total_files} files ({percentage}%)")

        # Update UI
        app.update()

    print("-" * 50)
    print("✅ Processing completed!")

    # Hide the progress bar
    time.sleep(1)
    app.setup_tab.hide_progress()
    print("▶️  Progress bar hidden")

    print("\n🎉 Progress bar test completed successfully!")
    print("\nℹ️  Real usage:")
    print("   1. Run: ./iniciar.sh")
    print("   2. Select a folder with PDFs")
    print("   3. Click 'Adicionar à fila'")
    print("   4. Watch the progress bar update as files are processed")
    print("   5. Click 'Cancelar' to stop processing if needed")

    # Keep window open for visual inspection
    print("\n⏳ Keeping window open for 5 seconds for visual inspection...")
    app.after(5000, app.quit)
    app.mainloop()

if __name__ == "__main__":
    try:
        simulate_processing()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
