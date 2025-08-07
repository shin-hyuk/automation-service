import requests
import json
from datetime import datetime
import time
import os
import sys
from dotenv import load_dotenv
import ccxt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import docker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import platform
import random

# Load environment variables
load_dotenv()

# Update log format with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print("\n=== LOGS ===")
print(f"Timestamp: {current_time}")
print(f"Current directory: {os.getcwd()}")

# Set up constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1i03nc79YYhFqQPz0knqN3jPoLvN8fMqe642AOE7Z3mk'
SHEET_NAME = 'Cypto_Asset'  # Sheet name as specified

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, 'utils', 'service-account.json')
print(f"Looking for service account file at: {SERVICE_ACCOUNT_FILE}")

# Define a global variable to store the starting row for cryptocurrencies
crypto_start_row = None

def setup_google_sheets():
    """Setup Google Sheets API"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"\nService account file not found: {SERVICE_ACCOUNT_FILE}")
            return None, None

        print(f"\nUsing service account file: {SERVICE_ACCOUNT_FILE}")

        # Load credentials from service account file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # Test the connection
        try:
            print("\nTesting connection to Google Sheets API...")
            result = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
            print(f"Successfully connected to spreadsheet: {result.get('properties', {}).get('title', 'Unknown')}")
            return service, sheet
        except HttpError as e:
            print(f"\nError accessing spreadsheet: {e}")
            return None, None

    except Exception as e:
        print(f"\nError in setup_google_sheets: {str(e)}")
        return None, None

def get_crypto_prices(symbols):
    """Get cryptocurrency prices for the given symbols using CCXT"""
    try:
        # Initialize exchanges
        binance = ccxt.binance()
        kraken = ccxt.kraken()
        kucoin = ccxt.kucoin()
        print("Initialized exchanges: Binance, Kraken, and KuCoin")

        # First, get USDT/USD price from Kraken
        usdt_usd_rate = 1.0  # Default fallback
        try:
            ticker = kraken.fetch_ticker('USDT/USD')
            if ticker and ticker.get('last') is not None:
                usdt_usd_rate = ticker['last']
                print(f"Got USDT/USD price from Kraken: {usdt_usd_rate}")
            else:
                print("No valid USDT/USD price found from Kraken, using 1.0")
        except Exception as e:
            print(f"Error fetching USDT/USD from Kraken: {e}")
            print("Using default USDT/USD rate of 1.0")

        prices = {}
        # Add USDT price to results if it's in our symbols list
        if 'USDT' in symbols:
            prices['USDT'] = usdt_usd_rate

        # Now fetch other crypto prices and convert to USD
        for symbol in symbols:
            if not symbol or symbol == 'USDT':  # Skip empty symbols and USDT (already handled)
                continue

            # Special handling for VISION - use KuCoin
            if symbol == 'VISION':
                try:
                    trading_symbol = 'VISION/USDT'
                    ticker = kucoin.fetch_ticker(trading_symbol)

                    if ticker and ticker.get('last') is not None:
                        # Convert from USDT to USD using the USDT/USD rate
                        price_in_usdt = ticker['last']
                        price_in_usd = price_in_usdt * usdt_usd_rate
                        prices[symbol] = price_in_usd
                        print(f"Got {symbol} price from KuCoin: {price_in_usdt} USDT = {price_in_usd} USD")
                    else:
                        print(f"No valid price found for {trading_symbol} on KuCoin")
                except Exception as e:
                    print(f"Error fetching {symbol} from KuCoin: {e}")
                continue

            try:
                # Get price in USDT
                trading_symbol = f"{symbol}/USDT" if '/' not in symbol else symbol
                ticker = binance.fetch_ticker(trading_symbol)

                if ticker and ticker.get('last') is not None:
                    # Convert from USDT to USD using the USDT/USD rate
                    price_in_usdt = ticker['last']
                    price_in_usd = price_in_usdt * usdt_usd_rate
                    prices[symbol] = price_in_usd
                    print(f"Converted {symbol} price: {price_in_usdt} USDT = {price_in_usd} USD (rate: {usdt_usd_rate})")
                else:
                    print(f"No valid price found for {trading_symbol}")
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")

        return prices

    except Exception as e:
        print(f"\nError getting crypto prices: {e}")
        print(f"Error details: {type(e)}")
        import traceback
        traceback.print_exc()
        return {}

def read_crypto_symbols(sheet):
    """Dynamically find the Currency header and read cryptocurrency symbols below it"""
    try:
        if not sheet:
            return []

        print("\nLooking for 'Currency' header in spreadsheet...")
        # First, read a larger range to find the "Currency" header
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1:A50"  # Read a large enough range to find the header
        ).execute()

        values = result.get('values', [])
        if not values:
            print("No data found in column A")
            return []

        # Find the "Currency" header
        currency_row = None
        for i, row in enumerate(values):
            if row and row[0] == "Currency":
                currency_row = i + 1  # 1-indexed row number
                print(f"Found 'Currency' header at row {currency_row}")
                break

        if currency_row is None:
            print("Currency header not found in column A")
            return []

        # Start reading symbols from TWO rows after the Currency header
        # because the header spans two rows
        start_row = currency_row + 2
        print(f"Reading cryptocurrency symbols starting from row {start_row}")

        # Read symbols until an empty cell is found
        symbols_result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{start_row}:A50"  # Read from start_row to row 50
        ).execute()

        symbols_values = symbols_result.get('values', [])

        # Extract symbols until an empty cell
        symbols = []
        for row in symbols_values:
            if not row or not row[0].strip():  # Stop at first empty cell
                break
            symbols.append(row[0])

        print(f"Found {len(symbols)} cryptocurrency symbols: {symbols}")
        # Store the start row for later use in update_crypto_prices
        global crypto_start_row
        crypto_start_row = start_row

        return symbols

    except Exception as e:
        print(f"Error reading symbols from Google Sheet: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def update_crypto_prices(sheet, prices):
    """Update cryptocurrency prices in column B for each symbol in column A"""
    try:
        if not sheet or not prices:
            return

        print("\nUpdating cryptocurrency prices in Google Sheet...")

        # Use the global crypto_start_row that was set in read_crypto_symbols
        global crypto_start_row

        # If crypto_start_row wasn't set, we can't proceed
        if not crypto_start_row:
            print("Cryptocurrency start row not determined. Cannot update prices.")
            return

        # Read symbols to ensure we're updating correct rows
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{crypto_start_row}:A{crypto_start_row+30}"  # Read more rows than needed
        ).execute()

        values = result.get('values', [])
        if not values:
            print("No symbols found in the spreadsheet")
            return

        # Prepare batch update
        data = []
        for i, row_data in enumerate(values):
            if not row_data or not row_data[0].strip():  # Stop at first empty row
                break

            symbol = row_data[0]
            if symbol in prices:
                # Update the corresponding row in column B
                current_row = crypto_start_row + i
                data.append({
                    'range': f"{SHEET_NAME}!B{current_row}",
                    'values': [[prices[symbol]]]
                })

        # Execute batch update
        if data:
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }

            result = sheet.values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()

            print(f"Updated {len(data)} price cells starting from row {crypto_start_row}")
        else:
            print("No prices to update")

    except Exception as e:
        print(f"Error updating Google Sheet: {str(e)}")
        import traceback
        traceback.print_exc()

def get_docker_client():
    system = platform.system()
    if system == "Windows":
        os.environ["DOCKER_HOST"] = "npipe:////./pipe/docker_engine"
    elif system == "Linux":
        os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
    return docker.from_env()

def start_docker_container(container_name, image_name):
    try:
        stop_docker_container(container_name)
    except Exception as e:
        print(f"Error stopping existing container: {e}")
    client = docker.from_env()
    client.containers.run(
        image_name,
        name=container_name,
        ports={"4444/tcp": 4444},
        detach=True,
    )

def stop_docker_container(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        print(f"Stopping container: {container_name}")
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        print(f"Container {container_name} not found. Skipping stop.")

def fetch_zerion_value():
    """Fetch wallet portfolio value from Zerion API using Basic Auth and no_filter for positions."""
    import base64
    
    # API configuration
    api_key = "zk_dev_fa79538d6b814d6bbde8f6870abdb8d1"
    address = "0x6286b9f080d27f860f6b4bb0226f8ef06cc9f2fc"
    url = f"https://api.zerion.io/v1/wallets/{address}/portfolio?currency=usd&filter[positions]=no_filter"
    
    try:
        print(f"Fetching portfolio data from Zerion API: {url}")
        
        # Create Basic Auth header
        auth_string = f"{api_key}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        # Set headers with Basic Auth
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"Using API key: {api_key}")
        print(f"Authorization header: Basic {encoded_auth}")
        
        # Make the API request with timeout and retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                print(f"API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("API Response received successfully")
                    print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Print the full response for debugging (first 2000 chars)
                    print("Full API Response:")
                    response_str = json.dumps(data, indent=2)
                    print(response_str[:2000] + "..." if len(response_str) > 2000 else response_str)
                    
                    # Extract the total portfolio value from the correct path
                    if (
                        'data' in data and
                        'attributes' in data['data'] and
                        'total' in data['data']['attributes'] and
                        'positions' in data['data']['attributes']['total']
                    ):
                        total_value = data['data']['attributes']['total']['positions']
                        print(f"Found portfolio value: {total_value}")
                        return str(int(float(total_value)))
                    else:
                        print("Could not find portfolio value in response at expected path.")
                        return None
                elif response.status_code == 401:
                    print("Authentication failed - check API key")
                    print(f"Response: {response.text}")
                    return None
                elif response.status_code == 429:
                    print(f"Rate limited (429). Waiting before retry {attempt + 1}/{max_retries}")
                    time.sleep(5)
                    continue
                else:
                    print(f"API request failed with status {response.status_code}")
                    print(f"Response: {response.text[:500]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    break
        
        return None
        
    except Exception as e:
        print(f"Error fetching Zerion value via API: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_zerion_value(sheet, value):
    try:
        if not sheet or value is None:
            print("Sheet not initialized or value is None.")
            return
        
        # Format the value as currency with commas (e.g., $51,853,576)
        try:
            numeric_value = float(value)
            formatted_value = f"${numeric_value:,.0f}"
            print(f"Formatted value: {formatted_value}")
        except (ValueError, TypeError):
            formatted_value = value
            print(f"Could not format value, using raw: {value}")
        
        data = [{
            'range': f"{SHEET_NAME}!I4",
            'values': [[formatted_value]]
        }]
        body = {
            'valueInputOption': 'USER_ENTERED',  # Changed from RAW to USER_ENTERED for better formatting
            'data': data
        }
        result = sheet.values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        print(f"Updated Zerion value at I4: {formatted_value}")
    except Exception as e:
        print(f"Error updating Zerion value in Google Sheet: {e}")

def main():
    try:
        # Setup Google Sheets
        service, sheet = setup_google_sheets()

        if not sheet:
            print("\nWarning: Google Sheets setup failed. Cannot proceed without spreadsheet access.")
            return

        # Read cryptocurrency symbols from the spreadsheet
        symbols = read_crypto_symbols(sheet)

        if not symbols:
            print("\nNo cryptocurrency symbols found in the spreadsheet")
            return

        # Get latest cryptocurrency prices
        prices = get_crypto_prices(symbols)

        if prices:
            print("\nLatest Cryptocurrency Prices:")
            print("\nSymbol\tPrice (USD)")
            print("-----------------")
            for symbol, price in prices.items():
                print(f"{symbol}\t${price}")

            # Update Google Sheet with prices
            update_crypto_prices(sheet, prices)
        else:
            print("\nNo cryptocurrency data retrieved")

        # Fetch Zerion value and update cell I4
        zerion_value = fetch_zerion_value()
        if zerion_value:
            update_zerion_value(sheet, zerion_value)
        else:
            print("Failed to fetch Zerion value.")

    except Exception as e:
        print(f"\nFatal error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
