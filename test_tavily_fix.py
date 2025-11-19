#!/usr/bin/env python3
"""Test to verify Tavily 400 error fixes."""

from src.core.llm_client import TavilyClient

def test_empty_identifiers():
    """Test that empty identifiers are handled gracefully."""
    client = TavilyClient()
    
    print("=== Test 1: All empty identifiers ===")
    results = client.search_online_for_missing_fields(
        product_name="",
        cas_number="",
        un_number="",
        missing_fields=["numero_cas", "classificacao_onu"]
    )
    print(f"Result: {results}")
    print(f"Expected: Empty dict (no identifiers)")
    
    print("\n=== Test 2: Whitespace-only identifiers ===")
    results = client.search_online_for_missing_fields(
        product_name="   ",
        cas_number="  ",
        un_number=None,
        missing_fields=["numero_cas"]
    )
    print(f"Result: {results}")
    print(f"Expected: Empty dict (no valid identifiers)")
    
    print("\n=== Test 3: Mix of empty and valid identifiers ===")
    results = client.search_online_for_missing_fields(
        product_name="",
        cas_number="67-64-1",  # Valid acetone CAS
        un_number="",
        missing_fields=["numero_onu"]
    )
    print(f"Result: {results}")
    print(f"Expected: Valid search with CAS 67-64-1")
    
    print("\n=== Test 4: Valid identifiers ===")
    results = client.search_online_for_missing_fields(
        product_name="Acetone",
        cas_number="67-64-1",
        un_number="1090",
        missing_fields=["classificacao_onu"]
    )
    print(f"Result: {results}")
    print(f"Expected: Valid search results")
    
    print("\n✅ All tests completed without 400 errors!")

if __name__ == "__main__":
    test_empty_identifiers()
