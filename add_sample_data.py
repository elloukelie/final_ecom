#!/usr/bin/env python3
"""
Quick script to add sample customers and orders for ML dashboard demonstration
"""

import requests
import json
from datetime import datetime, timedelta
import random

# Configuration
API_BASE = "http://localhost:8000/api/v1"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

def get_admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{API_BASE}/token", 
                           data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to authenticate: {response.status_code}")
        return None

def create_sample_customer(token, customer_data):
    """Create a sample customer"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_BASE}/customers/", 
                           json=customer_data, headers=headers)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"Failed to create customer: {response.status_code} - {response.text}")
        return None

def create_sample_order(token, order_data):
    """Create a sample order"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_BASE}/orders/", 
                           json=order_data, headers=headers)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"Failed to create order: {response.status_code} - {response.text}")
        return None

def main():
    print("🚀 Adding sample data for ML dashboard...")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("❌ Failed to get admin token")
        return
    
    print("✅ Got admin token")
    
    # Check existing customers
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/customers/", headers=headers)
    
    if response.status_code == 200:
        existing_customers = response.json()
        print(f"📊 Found {len(existing_customers)} existing customers")
        
        if len(existing_customers) >= 10:
            print("✅ Sufficient customer data already exists")
            print("🤖 ML dashboard should work properly now!")
            return
    
    # Sample customer data
    sample_customers = [
        {
            "first_name": "Alice",
            "last_name": "Johnson", 
            "email": "alice.johnson@example.com",
            "phone": "555-0101",
            "address": "123 Tech Street",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "USA"
        },
        {
            "first_name": "Bob",
            "last_name": "Smith",
            "email": "bob.smith@example.com", 
            "phone": "555-0102",
            "address": "456 Commerce Ave",
            "city": "New York",
            "state": "NY", 
            "postal_code": "10001",
            "country": "USA"
        },
        {
            "first_name": "Carol",
            "last_name": "Davis",
            "email": "carol.davis@example.com",
            "phone": "555-0103", 
            "address": "789 Market Road",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country": "USA"
        }
    ]
    
    # Create customers
    created_customers = []
    for customer_data in sample_customers:
        customer = create_sample_customer(token, customer_data)
        if customer:
            created_customers.append(customer)
            print(f"✅ Created customer: {customer_data['first_name']} {customer_data['last_name']}")
    
    print(f"✅ Created {len(created_customers)} sample customers")
    print("🤖 ML dashboard should now have data to display!")
    print("\n💡 Access the admin dashboard at: http://localhost:8501")
    print("📊 Go to ML Analytics Overview to see the results")

if __name__ == "__main__":
    main()
