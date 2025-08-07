#!/usr/bin/env python3
"""
Script to send sample.json data to webhook URL
"""
import requests
import json
import time
from typing import Dict, Any

# Configuration
WEBHOOK_URL = "https://n8n.ungr.app/webhook/a22755ec-26cb-4297-8d5f-8f5490d8b42b"
DATA_FILE = "data.json"
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'DataCollector-Webhook-Sender/1.0'
}

def load_data() -> Any:
    """Load clean data from data.json file"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"✅ Loaded {DATA_FILE}")
            
            if isinstance(data, list):
                print(f"📊 Found {len(data)} data records")
                if data and isinstance(data[0], dict):
                    print(f"🔍 Sample keys: {list(data[0].keys())[:5]}{'...' if len(data[0].keys()) > 5 else ''}")
            
            return data
                
    except FileNotFoundError:
        print(f"❌ Error: {DATA_FILE} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {DATA_FILE}: {str(e)}")
        return None

def send_to_webhook(data: Any) -> bool:
    """Send data to webhook URL"""
    try:
        print(f"🚀 Sending data to webhook...")
        print(f"🌐 URL: {WEBHOOK_URL}")
        print(f"📦 Data size: {len(json.dumps(data)) if data else 0} bytes")
        
        response = requests.post(
            WEBHOOK_URL,
            headers=HEADERS,
            json=data,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        # Print response details
        try:
            response_json = response.json()
            print(f"📄 Response:")
            print(json.dumps(response_json, indent=2)[:500] + "..." if len(str(response_json)) > 500 else json.dumps(response_json, indent=2))
        except:
            print(f"📄 Response Text: {response.text[:200]}..." if len(response.text) > 200 else response.text)
        
        # Check if successful
        if 200 <= response.status_code < 300:
            print("✅ SUCCESS: Data sent to webhook successfully!")
            return True
        else:
            print(f"❌ FAILED: Webhook returned status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out (30 seconds)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Connection failed - check webhook URL")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def send_individual_items(data: list) -> None:
    """Send each item in the array individually"""
    if not isinstance(data, list):
        print("❌ Data is not a list, cannot send individual items")
        return
    
    print(f"\n🔄 Sending {len(data)} items individually...")
    success_count = 0
    
    for i, item in enumerate(data):
        print(f"\n--- Item {i+1}/{len(data)} ---")
        if send_to_webhook(item):
            success_count += 1
        
        # Small delay between requests to avoid overwhelming the webhook
        if i < len(data) - 1:  # Don't delay after the last item
            time.sleep(0.5)
    
    print(f"\n📊 Summary: {success_count}/{len(data)} items sent successfully")

def main():
    """Main function"""
    print("🎯 Webhook Data Sender")
    print("=" * 50)
    
    # Load clean data
    data = load_data()
    if data is None:
        return
    
    # Show data info
    if isinstance(data, list):
        print(f"📋 Data type: Array with {len(data)} items")
        print(f"🔍 First item keys: {list(data[0].keys()) if data and isinstance(data[0], dict) else 'N/A'}")
    elif isinstance(data, dict):
        print(f"📋 Data type: Object with keys: {list(data.keys())}")
    else:
        print(f"📋 Data type: {type(data).__name__}")
    
    print("\n" + "=" * 50)
    
    # Send the entire data.json as one payload
    print("🚀 Sending entire data.json to webhook...")
    send_to_webhook(data)

if __name__ == "__main__":
    main()
