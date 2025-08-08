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
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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

def extract_and_write_crypto_data(sheet, all_holdings):
    """Extract unique crypto symbols from wallet holdings, order by USD value, and write to Google Sheets with quantities and values"""
    try:
        if not sheet or not all_holdings:
            return []
        
        # Aggregate holdings by symbol to get total USD value and quantity
        symbol_data = {}
        for holding in all_holdings:
            symbol = holding['symbol']
            usd_value = holding.get('usd_value', 0)
            quantity = holding.get('quantity', 0)
            
            if symbol in symbol_data:
                symbol_data[symbol]['usd_value'] += usd_value
                symbol_data[symbol]['quantity'] += quantity
            else:
                symbol_data[symbol] = {'usd_value': usd_value, 'quantity': quantity}
        
        # Sort by USD value (descending) and exclude fiat currencies
        sorted_data = sorted(symbol_data.items(), key=lambda x: abs(x[1]['usd_value']), reverse=True)
        crypto_data = [(symbol, data) for symbol, data in sorted_data if symbol not in ['USD', 'HKD', 'JPY']]
        crypto_symbols = [symbol for symbol, data in crypto_data]
        
        print(f"\nFound {len(crypto_symbols)} unique crypto symbols from wallet holdings")
        print(f"Top 5: {crypto_symbols[:5]}")
        
        # Find headers in the first row
        header_result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!1:5"
        ).execute()
        
        header_values = header_result.get('values', [])
        currency_col = None
        utgl_eth_col = None
        currency_row = None
        
        # Search for Currency, UTGL.ETH, and UTGL.ETH (value) headers
        utgl_eth_value_col = None
        for row_idx, row in enumerate(header_values):
            if row:
                for col_idx, cell in enumerate(row):
                    if cell == "Currency":
                        currency_col = col_idx  # 0-based column index
                        currency_row = row_idx + 1  # 1-based row index
                    elif cell == "UTGL.ETH":
                        utgl_eth_col = col_idx  # 0-based column index
                    elif cell == "UTGL.ETH (value)":
                        utgl_eth_value_col = col_idx  # 0-based column index
        
        if currency_col is None:
            print("Currency header not found")
            return crypto_symbols
        
        if utgl_eth_col is None:
            print("UTGL.ETH header not found")
            return crypto_symbols
        
        # Use UTGL.ETH (value) column if found, otherwise use next column after UTGL.ETH
        if utgl_eth_value_col is not None:
            value_col = utgl_eth_value_col
        else:
            value_col = utgl_eth_col + 1
        
        # Convert column indices to letters
        currency_col_letter = chr(ord('A') + currency_col)
        utgl_eth_col_letter = chr(ord('A') + utgl_eth_col)
        value_col_letter = chr(ord('A') + value_col)
        
        print(f"Found Currency at column {currency_col_letter}, UTGL.ETH at column {utgl_eth_col_letter}, Value at column {value_col_letter}")
        
        # Calculate totals
        total_portfolio_value = sum(data['usd_value'] for symbol, data in crypto_data)
        total_quantity = sum(data['quantity'] for symbol, data in crypto_data)
        
        # Write totals directly above the headers (one row up from headers)
        # If headers are in row 5, totals go in row 4
        total_row = currency_row
        
        # Total quantity above UTGL.ETH column
        quantity_total_range = f"{SHEET_NAME}!{utgl_eth_col_letter}{total_row}"
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=quantity_total_range,
            valueInputOption='RAW',
            body={'values': [[round(total_quantity, 2)]]}
        ).execute()
        
        # Total value above UTGL.ETH (value) column
        value_total_range = f"{SHEET_NAME}!{value_col_letter}{total_row}"
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=value_total_range,
            valueInputOption='RAW',
            body={'values': [[f"${total_portfolio_value:,.2f}"]]}
        ).execute()
        
        print(f"Updated totals - Quantity: {round(total_quantity, 2)} at {quantity_total_range}, Value: ${total_portfolio_value:,.2f} at {value_total_range}")
        
        # Write symbols starting from 2 rows after the Currency header
        start_row = currency_row + 2
        global crypto_start_row
        crypto_start_row = start_row
        
        # Prepare data for batch write
        currency_data = [[symbol] for symbol, data in crypto_data]
        quantity_data = [[round(data['quantity'], 2)] for symbol, data in crypto_data]
        value_data = [[f"${data['usd_value']:,.2f}"] for symbol, data in crypto_data]
        
        # Clear existing data in all columns
        clear_rows = 50
        clear_ranges = [
            f"{SHEET_NAME}!{currency_col_letter}{start_row}:{currency_col_letter}{start_row + clear_rows}",
            f"{SHEET_NAME}!{utgl_eth_col_letter}{start_row}:{utgl_eth_col_letter}{start_row + clear_rows}",
            f"{SHEET_NAME}!{value_col_letter}{start_row}:{value_col_letter}{start_row + clear_rows}"
        ]
        
        for clear_range in clear_ranges:
            clear_body = {'values': [[''] for _ in range(clear_rows + 1)]}
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=clear_range,
                valueInputOption='RAW',
                body=clear_body
            ).execute()
        
        # Write new data to all columns
        if crypto_data:
            end_row = start_row + len(crypto_data) - 1
            
            # Write symbols to Currency column
            currency_range = f"{SHEET_NAME}!{currency_col_letter}{start_row}:{currency_col_letter}{end_row}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=currency_range,
                valueInputOption='RAW',
                body={'values': currency_data}
            ).execute()
            
            # Write quantities to UTGL.ETH column
            quantity_range = f"{SHEET_NAME}!{utgl_eth_col_letter}{start_row}:{utgl_eth_col_letter}{end_row}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=quantity_range,
                valueInputOption='RAW',
                body={'values': quantity_data}
            ).execute()
            
            # Write USD values to next column
            value_range = f"{SHEET_NAME}!{value_col_letter}{start_row}:{value_col_letter}{end_row}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=value_range,
                valueInputOption='RAW',
                body={'values': value_data}
            ).execute()
            
            print(f"Updated {len(crypto_symbols)} entries across Currency, UTGL.ETH, and value columns")
        
        return crypto_symbols
        
    except Exception as e:
        print(f"Error extracting and writing crypto data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

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

        # Use the global crypto_start_row that was set in read_crypto_symbols
        global crypto_start_row

        # If crypto_start_row wasn't set, we can't proceed
        if not crypto_start_row:
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

            pass
        else:
            pass

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
        # Create Basic Auth header
        auth_string = f"{api_key}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        # Set headers with Basic Auth
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Make the API request with timeout and retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract the total portfolio value from the correct path
                    if (
                        'data' in data and
                        'attributes' in data['data'] and
                        'total' in data['data']['attributes'] and
                        'positions' in data['data']['attributes']['total']
                    ):
                        total_value = data['data']['attributes']['total']['positions']
                        return str(int(float(total_value)))
                    else:
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



def main():
    try:
        # Setup Google Sheets
        service, sheet = setup_google_sheets()

        if not sheet:
            print("\nWarning: Google Sheets setup failed. Cannot proceed without spreadsheet access.")
            return

        # Fetch Zerion wallet holdings first to get the crypto list
        print("\n=== ZERION WALLET HOLDINGS ===")
        all_holdings = fetch_all_zerion_wallets()
        
        # Extract crypto data from wallet holdings and write to Google Sheets
        symbols = extract_and_write_crypto_data(sheet, all_holdings)

        if not symbols:
            print("\nNo cryptocurrency symbols found in wallet holdings")
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

        # Fetch and print most recent data from database
        print("\n=== DATABASE DATA ===")
        fetch_latest_database_record()

    except Exception as e:
        print(f"\nFatal error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

def fetch_latest_database_record():
    """Fetch and print the most recent record from utgl_gary_wealth_records table"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Supabase credentials not found in environment variables")
            return
        
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase database")
        
        # Fetch the most recent record ordered by date
        result = supabase.table('utgl_gary_wealth_records')\
            .select('*')\
            .order('date', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            latest_record = result.data[0]
            print(f"\n📊 Most Recent Database Record:")
            print(f"🕐 Date: {latest_record.get('date')}")
            print(f"🔍 ID: {latest_record.get('id', 'N/A')}")
            
            # Extract and display all crypto entries with non-zero balances
            data_content = latest_record.get('data', {})
            crypto_entries = extract_nonzero_crypto_entries(data_content)
            
            print(f"\n💰 ALL CRYPTO ENTRIES WITH NON-ZERO BALANCES:")
            print("-" * 70)
            if crypto_entries:
                for entry in crypto_entries:
                    print(f"• {entry['symbol']}: {entry['balance']}")
                print(f"\n📊 Total entries: {len(crypto_entries)}")
            else:
                print("No crypto entries with non-zero balances found")
            print("-" * 70)
            
        else:
            print("❌ No records found in utgl_gary_wealth_records table")
            
    except Exception as e:
        print(f"❌ Database fetch error: {e}")
        import traceback
        traceback.print_exc()

def fetch_all_zerion_wallets():
    """Fetch holdings from all specified Zerion wallets and show total holdings. Returns all holdings for further processing."""
    import base64
    
    # Wallet addresses to check - using different APIs for different blockchain types
    wallets = [
        {
            "name": "Zerion Wallet", 
            "address": "0x6286b9f080D27f860F6b4bb0226F8EF06CC9F2Fc",
            "expected": "$57M+ DeFi positions (includes 2,000 VISION)",
            "type": "evm",
            "api": "zerion"
        },
        {
            "name": "SOL Wallet",
            "address": "9ZxWx53d6rJTuay8PNaVx3knvyc53GUUvn4e4riH8Wr6",
            "expected": "10 SOL",
            "type": "solana", 
            "api": "solana_rpc"
        },
        {
            "name": "BTC Wallet",
            "address": "bc1pg23parj9nplsgthlgj0ppzcc2u3vleseg33hy390esp3py5sgrxqdy2k8r",
            "expected": "3.5961 BTC",
            "type": "bitcoin",
            "api": "blockstream"
        }
    ]
    
    api_key = "zk_dev_fa79538d6b814d6bbde8f6870abdb8d1"
    all_holdings = []
    
    # Fetch all wallet data silently
    wallet_results = {}
    
    for wallet in wallets:
        # Route to appropriate API based on wallet type
        if wallet['api'] == 'zerion':
            holdings = fetch_wallet_holdings_zerion(api_key, wallet['address'], wallet['name'])
        elif wallet['api'] == 'solana_rpc':
            holdings = fetch_wallet_holdings_solana(wallet['address'], wallet['name'])
        elif wallet['api'] == 'blockstream':
            holdings = fetch_wallet_holdings_bitcoin(wallet['address'], wallet['name'])
        else:
            holdings = None
            
        if holdings:
            all_holdings.extend(holdings)
            wallet_results[wallet['name']] = holdings
        else:
            wallet_results[wallet['name']] = []
    
    # Create categorized portfolio summary
    print(f"\n🏆 GARY'S PORTFOLIO")
    print("=" * 80)
    
    if all_holdings:
        total_portfolio_usd = sum(holding.get('usd_value', 0) for holding in all_holdings)
        print(f"💰 Total Portfolio Value: ${total_portfolio_usd:,.2f}")
        print("=" * 80)
        
        # Show holdings by wallet category
        for wallet_name, holdings in wallet_results.items():
            if holdings:
                wallet_total_usd = sum(holding.get('usd_value', 0) for holding in holdings)
                print(f"\n📂 {wallet_name.upper()}")
                print(f"💵 Wallet Value: ${wallet_total_usd:,.2f}")
                print("-" * 50)
                
                # Aggregate holdings by symbol within this wallet
                wallet_symbols = {}
                for holding in holdings:
                    symbol = holding['symbol']
                    quantity = holding['quantity']
                    usd_value = holding.get('usd_value', 0)
                    
                    if symbol in wallet_symbols:
                        wallet_symbols[symbol]['quantity'] += quantity
                        wallet_symbols[symbol]['usd_value'] += usd_value
                    else:
                        wallet_symbols[symbol] = {
                            'quantity': quantity,
                            'usd_value': usd_value
                        }
                
                # Sort by USD value (descending) and show top holdings
                sorted_wallet_holdings = sorted(wallet_symbols.items(), 
                                               key=lambda x: x[1]['usd_value'], reverse=True)
                
                # Show all holdings for all wallets
                display_limit = len(sorted_wallet_holdings)
                
                for i, (symbol, data) in enumerate(sorted_wallet_holdings[:display_limit]):
                    quantity = data['quantity']
                    usd_value = data['usd_value']
                    debt_indicator = " 🔴DEBT" if quantity < 0 or usd_value < 0 else ""
                    quantity_str = f"{quantity:,.6f}".rstrip('0').rstrip('.')
                    
                    print(f"{i+1:2d}. {symbol}: {quantity_str} (${usd_value:,.2f}){debt_indicator}")
                
                if len(sorted_wallet_holdings) > display_limit:
                    remaining = len(sorted_wallet_holdings) - display_limit
                    remaining_value = sum(data['usd_value'] for _, data in sorted_wallet_holdings[display_limit:])
                    print(f"... and {remaining} more tokens (${remaining_value:,.2f})")
        
        print("\n" + "=" * 80)
        print(f"📈 Total unique assets: {len(set(h['symbol'] for h in all_holdings))}")
        print(f"🏦 Wallets tracked: {len([w for w in wallet_results.values() if w])}")
        
        # Return all holdings for further processing
        return all_holdings
    else:
        print("❌ No holdings found across all wallets")
        return []

def fetch_wallet_holdings_zerion(api_key, address, wallet_name):
    """Fetch holdings for a single wallet from Zerion API using the same method as the working portfolio endpoint"""
    import base64
    
    # Use the fungible positions endpoint to get individual token holdings
    url = f"https://api.zerion.io/v1/wallets/{address}/positions?filter[positions]=no_filter"
    
    try:
        # Create Basic Auth header (same as working function)
        auth_string = f"{api_key}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            holdings = []
            
            # Save the full raw response to file for debugging (silently)
            try:
                with open('raw.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                pass  # Silent failure
            
            # Parse positions endpoint response - positions should be in data array
            if 'data' in data and isinstance(data['data'], list):
                
                for position in data['data']:
                    if isinstance(position, dict) and 'type' in position and position['type'] == 'positions':
                        if 'attributes' in position:
                            attrs = position['attributes']
                            
                            # Get token info, quantity, and USD value
                            if 'fungible_info' in attrs and 'quantity' in attrs:
                                token = attrs['fungible_info']
                                
                                # Handle quantity object format from positions endpoint
                                quantity_data = attrs['quantity']
                                if isinstance(quantity_data, dict):
                                    # Use the float value from the quantity object
                                    quantity = float(quantity_data.get('float', 0))
                                else:
                                    # Fallback for simple number format
                                    quantity = float(quantity_data)
                                
                                # Get USD value of this position (handle None/null values)
                                value_raw = attrs.get('value', 0)
                                usd_value = float(value_raw) if value_raw is not None else 0.0
                                
                                # Check if this is a debt position (loan = borrowed money)
                                position_type = attrs.get('position_type', '')
                                is_debt = position_type == 'loan'
                                
                                # For debt positions, make quantity and USD value negative
                                if is_debt:
                                    quantity = -abs(quantity)  # Ensure negative
                                    usd_value = -abs(usd_value)  # Ensure negative USD value
                                
                                # Include positions with non-zero quantities OR non-zero USD values (including negative debt)
                                if quantity != 0 or usd_value != 0:
                                    symbol = token.get('symbol', 'UNKNOWN')
                                    name = token.get('name', symbol)
                                    position_name = attrs.get('name', f"{symbol} Position")
                                    debt_indicator = " 🔴DEBT" if is_debt else ""
                                    
                                    # Skip Aave aTokens to avoid double counting with underlying assets
                                    # aTokens represent deposited funds in Aave and would duplicate the underlying token values
                                    if symbol.startswith('aEth') or symbol.startswith('aglaMerkl'):
                                        continue
                                    
                                    # Skip tokens that Zerion hides: not displayable or unpriced (null value/price=0)
                                    # This matches Zerion's UI behavior of hiding dust/spam tokens
                                    position_flags = attrs.get('flags', {})
                                    is_displayable = position_flags.get('displayable', True)
                                    raw_value = attrs.get('value')
                                    price = attrs.get('price', 0)
                                    
                                    # Skip if not displayable OR if unpriced (unless it's a debt position)
                                    if not is_displayable or (raw_value is None and price == 0 and not is_debt):
                                        continue
                                    
                                    holdings.append({
                                        'wallet': wallet_name,
                                        'symbol': symbol,
                                        'name': name,
                                        'position_name': position_name + debt_indicator,
                                        'quantity': quantity,
                                        'usd_value': usd_value,
                                        'is_debt': is_debt,
                                        'address': address[:10] + "..."
                                    })
            
            # Holdings processed - details will be shown in final summary
            else:
                print(f"  ⚠️ Could not find positions data for {wallet_name}")
                print(f"  📄 Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if 'data' in data:
                    print(f"  📄 data type: {type(data['data'])}")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"  📄 first data item: {data['data'][0].keys() if isinstance(data['data'][0], dict) else 'Not a dict'}")
                    elif isinstance(data['data'], dict):
                        print(f"  📄 data keys: {list(data['data'].keys())}")
            
            return holdings
            
        elif response.status_code == 401:
            print(f"  ❌ Authentication failed for {wallet_name}")
            return None
        elif response.status_code == 404:
            print(f"  ❌ Wallet not found: {wallet_name}")
            return None
        else:
            print(f"  ❌ API error {response.status_code} for {wallet_name}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error fetching {wallet_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_wallet_holdings_solana(address, wallet_name):
    """Fetch holdings for a Solana wallet using Solana RPC API"""
    try:
        # Solana RPC endpoint (you can use a free public RPC or get an API key from services like Alchemy, QuickNode)
        url = "https://api.mainnet-beta.solana.com"
        
        # Get account info for the wallet
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                address,
                {"encoding": "base64"}
            ]
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Get token accounts for this wallet
            token_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},  # SPL Token program
                    {"encoding": "jsonParsed"}
                ]
            }
            
            token_response = requests.post(url, json=token_payload, headers=headers, timeout=30)
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                holdings = []
                
                # Check SOL balance first
                if 'result' in data and data['result'] and 'value' in data['result']:
                    sol_lamports = data['result']['value']['lamports'] if data['result']['value'] else 0
                    sol_balance = sol_lamports / 1_000_000_000  # Convert lamports to SOL
                    
                    if sol_balance > 0:
                        # Calculate USD value (approximate using $175 per SOL)
                        sol_usd_value = sol_balance * 175  # You could fetch real price from API
                        
                        holdings.append({
                            'wallet': wallet_name,
                            'symbol': 'SOL',
                            'name': 'Solana',
                            'quantity': sol_balance,
                            'usd_value': sol_usd_value,
                            'address': address[:10] + "..."
                        })
                        pass  # SOL added to holdings silently
                
                return holdings
            else:
                print(f"  ❌ Solana token API error: {token_response.status_code}")
                return None
        else:
            print(f"  ❌ Solana RPC error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error fetching Solana wallet: {e}")
        return None

def fetch_wallet_holdings_bitcoin(address, wallet_name):
    """Fetch holdings for a Bitcoin wallet using Blockstream API"""
    try:
        # Blockstream API endpoint
        url = f"https://blockstream.info/api/address/{address}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Get BTC balance
            balance_satoshis = data.get('chain_stats', {}).get('funded_txo_sum', 0) - data.get('chain_stats', {}).get('spent_txo_sum', 0)
            btc_balance = balance_satoshis / 100_000_000  # Convert satoshis to BTC
            
            holdings = []
            if btc_balance > 0:
                # Calculate USD value (approximate using $117K per BTC)
                btc_usd_value = btc_balance * 117000  # You could fetch real price from API
                
                holdings.append({
                    'wallet': wallet_name,
                    'symbol': 'BTC',
                    'name': 'Bitcoin',
                    'quantity': btc_balance,
                    'usd_value': btc_usd_value,
                    'address': address[:10] + "..."
                })
                pass  # BTC added to holdings silently
            
            return holdings
        else:
            print(f"  ❌ Blockstream API error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error fetching Bitcoin wallet: {e}")
        return None

def extract_nonzero_crypto_entries(data):
    """Extract and aggregate cryptocurrency entries by symbol, then filter out zero balances"""
    symbol_totals = {}
    
    def process_item(item, account_info=""):
        """Process a single user/account item"""
        if isinstance(item, dict) and 'balances' in item:
            balances = item['balances']
            if isinstance(balances, dict):
                for symbol, balance in balances.items():
                    # Check if balance is not None
                    if balance is not None:
                        # Aggregate balances by symbol
                        if symbol in symbol_totals:
                            symbol_totals[symbol] += balance
                        else:
                            symbol_totals[symbol] = balance
    
    if isinstance(data, list):
        # If data is a list of user accounts
        for i, item in enumerate(data):
            account_info = f"Account {i+1}"
            if isinstance(item, dict):
                if 'accountId' in item:
                    account_info = f"Account {item['accountId']}"
                elif 'userId' in item:
                    account_info = f"User {item['userId'][:8]}..."
            process_item(item, account_info)
    elif isinstance(data, dict):
        # If data is a single account object
        if 'balances' in data:
            account_info = "Single Account"
            if 'accountId' in data:
                account_info = f"Account {data['accountId']}"
            elif 'userId' in data:
                account_info = f"User {data['userId'][:8]}..."
            process_item(data, account_info)
        else:
            # Check if it might be nested differently
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    nested_entries = extract_nonzero_crypto_entries(value)
                    # Merge nested results into our symbol_totals
                    for entry in nested_entries:
                        symbol = entry['symbol']
                        balance = entry['balance']
                        if symbol in symbol_totals:
                            symbol_totals[symbol] += balance
                        else:
                            symbol_totals[symbol] = balance
                    return [{'symbol': symbol, 'balance': balance} for symbol, balance in symbol_totals.items() if balance != 0]
    
    # Convert aggregated totals to list format and filter out zero balances
    crypto_entries = []
    for symbol, total_balance in symbol_totals.items():
        if total_balance != 0:  # Only include non-zero balances
            crypto_entries.append({
                'symbol': symbol,
                'balance': total_balance
            })
    
    # Sort by symbol alphabetically
    crypto_entries.sort(key=lambda x: x['symbol'])
    
    return crypto_entries

if __name__ == "__main__":
    main()
