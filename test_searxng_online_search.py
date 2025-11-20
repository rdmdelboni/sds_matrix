#!/usr/bin/env python
"""Test script for SearXNG online search functionality."""

import os
import sys

# set environment to use SearXNG
os.environ['ONLINE_SEARCH_PROVIDER'] = 'searxng'
os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'

from src.core.searxng_client import SearXNGClient

def test_searxng_search():
    """Test SearXNG online search."""
    print("=" * 60)
    print("Testing SearXNG Online Search")
    print("=" * 60)
    
    # Initialize client
    print("\n1️⃣ Initializing SearXNG client...")
    client = SearXNGClient()
    print(f"   ✅ Client initialized")
    print(f"   📍 Instance: {client.instances[0]}")
    print(f"   ⚡ Rate limit: {client.rate_limiter.rate} req/sec")
    print(f"   💾 Cache: {'enabled' if client.cache_enabled else 'disabled'}")
    
    # Test search
    print("\n2️⃣ Testing search for missing fields...")
    test_data = {
        'product_name': 'Ethanol',
        'cas_number': '64-17-5',
        'missing_fields': ['numero_onu', 'classificacao_onu', 'grupo_embalagem']
    }
    
    print(f"   Product: {test_data['product_name']}")
    print(f"   CAS: {test_data['cas_number']}")
    print(f"   Searching for: {', '.join(test_data['missing_fields'])}")
    
    result = client.search_online_for_missing_fields(**test_data)
    
    # Display results
    print("\n3️⃣ Search results:")
    for field, data in result.items():
        value = data.get('value', 'N/A')
        confidence = data.get('confidence', 0.0)
        context = data.get('context', 'N/A')
        
        # Truncate long values
        if len(str(value)) > 80:
            value = str(value)[:77] + "..."
        
        print(f"\n   {field}:")
        print(f"   • Value: {value}")
        print(f"   • Confidence: {confidence:.2f}")
        print(f"   • Source: {context}")
    
    print("\n" + "=" * 60)
    print("✅ SearXNG online search is working!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_searxng_search()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
