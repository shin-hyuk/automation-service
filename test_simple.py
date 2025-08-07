#!/usr/bin/env python3
"""
Simple test without database dependency
"""
import requests

API_URL = "https://data-collector-601408578579.us-central1.run.app"

def test_simple():
    """Test if the service is even reachable"""
    try:
        print(f"🧪 Testing simple connection to: {API_URL}")
        response = requests.get(API_URL, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text[:200]}...")
        
        if response.status_code == 503:
            print("❌ Service Unavailable - Likely deployment/config issue")
            print("💡 Suggestions:")
            print("   1. Check Cloud Run logs in Google Console")
            print("   2. Verify env.yaml was deployed correctly")
            print("   3. Check Supabase connection")
            print("   4. Try redeploying the service")
        
    except Exception as e:
        print(f"💥 Connection Error: {str(e)}")

if __name__ == "__main__":
    test_simple()
