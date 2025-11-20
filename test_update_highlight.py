#!/usr/bin/env python
"""Test script to demonstrate the updated field highlighting feature."""

import os
import sys
from pathlib import Path

# Set environment to use SearXNG
os.environ['ONLINE_SEARCH_PROVIDER'] = 'searxng'
os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'

from src.database.duckdb_manager import DuckDBManager


def main():
    """Show how the system detects and highlights updated fields."""
    print("=" * 70)
    print("Updated Field Highlighting Feature - How It Works")
    print("=" * 70)
    
    db = DuckDBManager()
    
    # Get a sample document
    results = db.fetch_recent_results(limit=1)
    if not results:
        print("\n⚠️  No documents found in database.")
        print("   Process at least one document first.")
        return
    
    doc = results[0]
    doc_id = doc['id']
    filename = doc['filename']
    
    print(f"\n📄 Example Document: {filename}")
    print(f"   ID: {doc_id}")
    
    print("\n" + "=" * 70)
    print("How the Feature Works:")
    print("=" * 70)
    
    print("""
1️⃣  BEFORE REPROCESSING:
   - System stores current field values and confidence scores
   - Example: numero_onu = "1170" (confidence: 0.50)

2️⃣  DURING REPROCESSING:
   - Document is reprocessed with mode="online"
   - Online search finds better/new values
   - Example: numero_onu = "1170" (confidence: 0.85) ✨

3️⃣  AFTER REPROCESSING:
   - System compares new vs old values
   - Detects changes in:
     • Value changed (e.g., "-" → "1170")
     • Confidence improved (e.g., 0.50 → 0.85)
   
4️⃣  IN THE PROCESSING TAB:
   - Updated fields show with ✨ icon
   - Row has YELLOW BACKGROUND highlight
   - Regular fields keep normal background
   
Example Display:
┌──────────────────────────────────────────────────────────┐
│ Documento    │ Status     │ Produto  │ ONU      │ CAS   │
├──────────────────────────────────────────────────────────┤
│ example.pdf  │ Concluído  │ Ethanol  │ ✨ 1170  │ 64-17-5│  ← YELLOW BG
└──────────────────────────────────────────────────────────┘

Legend:
  ✨ = Field was updated (new value or better confidence)
  Yellow Background = At least one field was updated
  Normal Background = No changes detected
    """)
    
    print("\n" + "=" * 70)
    print("To See It In Action:")
    print("=" * 70)
    print("""
1. Run the application:
   source venv/bin/activate && python main.py

2. Go to Processing Tab

3. Select a document that has missing fields

4. Set mode to "online"

5. Click "Iniciar Processamento"

6. Watch for:
   - Status changes to "Processando" (values saved)
   - Status changes to "Concluído" (comparison done)
   - Row turns YELLOW if fields were updated
   - Updated fields show ✨ icon

7. Compare with Results Tab to see improvements
    """)
    
    print("=" * 70)
    print("✅ Feature is ready to use!")
    print("=" * 70)


if __name__ == "__main__":
    main()
