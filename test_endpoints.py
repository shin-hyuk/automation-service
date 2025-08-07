#!/usr/bin/env python3
"""
Test script for Data Collector API endpoints
Tests all available endpoints with the deployed Cloud Run URL
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Configuration
API_URL = os.getenv('API_URL', 'https://data-collector-601408578579.us-central1.run.app')
HEADERS = {'Content-Type': 'application/json'}

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint and print results"""
    url = f"{API_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {method} {endpoint}")
    print(f"📝 Description: {description}")
    print(f"🌐 URL: {url}")
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, headers=HEADERS, json=data)
        
        print(f"📊 Status Code: {response.status_code}")
        
        # Pretty print JSON response
        try:
            json_response = response.json()
            print(f"📄 Response:")
            print(json.dumps(json_response, indent=2))
        except:
            print(f"📄 Response: {response.text}")
            
        # Status indicator
        if 200 <= response.status_code < 300:
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
            
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        print("❌ CONNECTION FAILED")

def run_all_tests():
    """Run all endpoint tests"""
    print("🚀 Starting Data Collector API Tests")
    print(f"🎯 Target URL: {API_URL}")
    
    # Test 1: Root endpoint
    test_endpoint(
        'GET', 
        '/', 
        description="API information and available endpoints"
    )
    
    # Test 2: Health check
    test_endpoint(
        'GET', 
        '/health', 
        description="Application and database health status"
    )
    
    # Test 3: Gary wealth endpoint info (GET)
    test_endpoint(
        'GET', 
        '/utgl-gary-wealth-data', 
        description="Endpoint documentation and example payload"
    )
    
    # Test 4: Submit Gary wealth data (POST)
    test_data = {
        "client_id": "GARY001_TEST",
        "wealth_data": {
            "assets": 1500000,
            "liabilities": 200000,
            "net_worth": 1300000,
            "investment_portfolio": {
                "stocks": 800000,
                "bonds": 300000,
                "real_estate": 400000
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "test_run": True
        }
    }
    
    test_endpoint(
        'POST', 
        '/utgl-gary-wealth-data', 
        data=test_data,
        description="Submit test Gary wealth data"
    )
    
    # Test 5: Invalid endpoint (404 test)
    test_endpoint(
        'GET', 
        '/invalid-endpoint', 
        description="Test 404 error handling"
    )
    
    print(f"\n{'='*60}")
    print("🎉 All tests completed!")
    print(f"🌐 API URL: {API_URL}")

if __name__ == "__main__":
    run_all_tests()
