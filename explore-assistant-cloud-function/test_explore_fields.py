#!/usr/bin/env python3
"""
Test script to explore what fields are actually available in the sales_demo_the_look:order_items explore
"""

import json
import logging
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
        print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not available")

import looker_sdk

def explore_available_fields():
    """Examine what fields are actually available in the explore"""
    try:
        print("=== INITIALIZING LOOKER SDK ===")
        sdk = looker_sdk.init40()
        user = sdk.me()
        print(f"Connected to Looker as: {user.email}")
        
        model_name = "sales_demo_the_look"
        explore_name = "order_items"
        
        print(f"\n=== EXAMINING EXPLORE: {model_name}:{explore_name} ===")
        
        # Get detailed explore information
        explore_detail = sdk.lookml_model_explore(
            lookml_model_name=model_name,
            explore_name=explore_name,
            fields='sets,fields'
        )
        
        print(f"\n=== EXPLORE STRUCTURE ===")
        print(f"Has sets: {bool(explore_detail.sets)}")
        print(f"Has fields: {bool(explore_detail.fields)}")
        
        # Check sets
        if explore_detail.sets:
            print(f"\n=== SETS ({len(explore_detail.sets)}) ===")
            for set_info in explore_detail.sets:
                print(f"  Set: {set_info.name}")
                if set_info.value:
                    print(f"    Fields: {set_info.value[:10]}...")  # Show first 10
                    if 'inventory_items.product_brand' in set_info.value:
                        print(f"    *** Contains inventory_items.product_brand ***")
        
        # Check available fields
        if explore_detail.fields:
            print(f"\n=== AVAILABLE DIMENSIONS ===")
            if explore_detail.fields.dimensions:
                inventory_dimensions = []
                product_dimensions = []
                other_dimensions = []
                
                for dimension in explore_detail.fields.dimensions:
                    field_key = f"{dimension.view}.{dimension.name}" if dimension.view else dimension.name
                    
                    if 'inventory' in field_key.lower():
                        inventory_dimensions.append(field_key)
                    elif 'product' in field_key.lower():
                        product_dimensions.append(field_key)
                    else:
                        other_dimensions.append(field_key)
                
                print(f"  Inventory-related dimensions ({len(inventory_dimensions)}):")
                for field in inventory_dimensions[:15]:  # Show first 15
                    print(f"    {field}")
                if len(inventory_dimensions) > 15:
                    print(f"    ... and {len(inventory_dimensions) - 15} more")
                
                print(f"  Product-related dimensions ({len(product_dimensions)}):")
                for field in product_dimensions[:15]:  # Show first 15
                    print(f"    {field}")
                if len(product_dimensions) > 15:
                    print(f"    ... and {len(product_dimensions) - 15} more")
                    
                print(f"  Total dimensions: {len(explore_detail.fields.dimensions)}")
                
                # Check if our target field exists
                target_field = "inventory_items.product_brand"
                found = False
                for dimension in explore_detail.fields.dimensions:
                    field_key = f"{dimension.view}.{dimension.name}" if dimension.view else dimension.name
                    if field_key == target_field:
                        found = True
                        print(f"\n  *** FOUND TARGET FIELD: {field_key} ***")
                        print(f"    View: {dimension.view}")
                        print(f"    Name: {dimension.name}")
                        print(f"    Label: {dimension.label}")
                        print(f"    Description: {dimension.description}")
                        break
                
                if not found:
                    print(f"\n  *** TARGET FIELD '{target_field}' NOT FOUND ***")
                    
                    # Look for similar fields
                    similar_fields = []
                    for dimension in explore_detail.fields.dimensions:
                        field_key = f"{dimension.view}.{dimension.name}" if dimension.view else dimension.name
                        if 'brand' in field_key.lower():
                            similar_fields.append(field_key)
                    
                    if similar_fields:
                        print(f"  Similar brand-related fields found:")
                        for field in similar_fields:
                            print(f"    {field}")
            else:
                print("  No dimensions found")
                
            print(f"\n=== AVAILABLE MEASURES ===")
            if explore_detail.fields.measures:
                print(f"  Total measures: {len(explore_detail.fields.measures)}")
                # Show first few measures
                for measure in explore_detail.fields.measures[:10]:
                    field_key = f"{measure.view}.{measure.name}" if measure.view else measure.name
                    print(f"    {field_key}")
            else:
                print("  No measures found")
        
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_available_fields()
