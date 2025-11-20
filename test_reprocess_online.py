#!/usr/bin/env python
"""Test script to verify online search runs when reprocessing documents."""

import os
import sys
from pathlib import Path

# set environment to use SearXNG
os.environ['ONLINE_SEARCH_PROVIDER'] = 'searxng'
os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'

from src.database.duckdb_manager import DuckDBManager
from src.core.document_processor import DocumentProcessor
from src.core.searxng_client import SearXNGClient
from src.utils.config import DATA_DIR

def test_reprocess_with_online_search():
    """Test that reprocessing a document triggers online search."""
    print("=" * 70)
    print("Testing Document Reprocessing with Online Search")
    print("=" * 70)
    
    # Initialize components
    db = DuckDBManager()
    searxng = SearXNGClient()
    
    # Check SearXNG is available
    if not searxng.test_connection():
        print("\n❌ ERROR: SearXNG is not running!")
        print("   Run: ./setup_searxng.sh")
        sys.exit(1)
    
    print(f"\n✅ SearXNG connected: {searxng.instances[0]}")
    
    # Get a sample processed document from database
    results = db.fetch_recent_results(limit=5)
    
    if not results:
        print("\n⚠️  No documents found in database.")
        print("   Process at least one document first.")
        sys.exit(0)
    
    # Select first document
    doc = results[0]
    doc_id = doc['id']
    filename = doc['filename']
    file_path = Path(doc['file_path'])
    
    print(f"\n📄 Document: {filename}")
    print(f"   ID: {doc_id}")
    print(f"   Path: {file_path}")
    
    # Show current field values
    print(f"\n📊 Current field status:")
    field_details = db.get_field_details(doc_id)
    
    missing_count = 0
    for field_name, details in field_details.items():
        value = details.get('value', 'NAO ENCONTRADO')
        confidence = details.get('confidence', 0.0)
        status = details.get('validation_status', 'unknown')
        
        # Truncate long values
        display_value = str(value)[:40]
        if len(str(value)) > 40:
            display_value += "..."
        
        status_icon = "✅" if confidence >= 0.7 else "⚠️"
        print(f"   {status_icon} {field_name}: {display_value} (conf: {confidence:.2f})")
        
        if confidence < 0.7 or value == "NAO ENCONTRADO":
            missing_count += 1
    
    if missing_count == 0:
        print(f"\n✅ All fields have good confidence, but will still test reprocessing")
    else:
        print(f"\n⚠️  Found {missing_count} fields with low confidence or missing")
    
    # Reprocess with online mode
    print(f"\n🔄 Reprocessing document with online search...")
    
    if not file_path.exists():
        print(f"\n❌ File not found: {file_path}")
        print("   File may have been moved or deleted.")
        sys.exit(1)
    
    processor = DocumentProcessor(
        db_manager=db,
        online_search_client=searxng,
    )
    
    try:
        processor.process(file_path, mode="online")
        print(f"\n✅ Reprocessing completed!")
        
        # Show updated fields
        print(f"\n📊 Updated field status:")
        updated_details = db.get_field_details(doc_id)
        
        improved_count = 0
        for field_name, details in updated_details.items():
            old_details = field_details.get(field_name, {})
            old_conf = old_details.get('confidence', 0.0)
            new_conf = details.get('confidence', 0.0)
            
            value = details.get('value', 'NAO ENCONTRADO')
            display_value = str(value)[:40]
            if len(str(value)) > 40:
                display_value += "..."
            
            if new_conf > old_conf:
                print(f"   ⬆️  {field_name}: {display_value} (conf: {old_conf:.2f} → {new_conf:.2f})")
                improved_count += 1
            else:
                status_icon = "✅" if new_conf >= 0.7 else "⚠️"
                print(f"   {status_icon} {field_name}: {display_value} (conf: {new_conf:.2f})")
        
        print(f"\n" + "=" * 70)
        if improved_count > 0:
            print(f"✅ SUCCESS: {improved_count} field(s) improved via online search!")
        else:
            print(f"✅ Reprocessing completed (no confidence improvements)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_reprocess_with_online_search()
