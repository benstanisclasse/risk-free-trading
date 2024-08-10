import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
import threading

# Class to handle Alpaca API interactions
class AlpacaAPI:
    def __init__(self, api_key, secret_key):
        # Initialize API credentials
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        }

    # Method to fetch options data from the Alpaca API
    def get_options_data(self, url):
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

    # Method to fetch current stock prices from the Alpaca API
    def get_current_prices(self, url):
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

    # Method to check the market clock
    def get_market_clock(self):
        url = "https://paper-api.alpaca.markets/v2/clock"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

# Class to manage contract information and formatting
class ContractInfo:
    def __init__(self, alpaca_api):
        self.alpaca_api = alpaca_api

    # Method to get contract details for a specific option symbol
    def get_contract_data(self, symbol):
        url = f"https://paper-api.alpaca.markets/v2/options/contracts/{symbol}"
        response = requests.get(url, headers=self.alpaca_api.headers)
        return response.json()

    # Method to format the contract symbol based on its attributes
    def format_symbol(self, data):
        expiration_date = data.get('expiration_date', 'N/A')
        root_symbol = data.get('root_symbol', 'N/A')
        option_type = data.get('type', 'N/A')
        strike_price = data.get('strike_price', 'N/A')

        # Convert option type to 'P' for put and 'C' for call
        if option_type.lower() == 'put':
            option_type = 'P'
        elif option_type.lower() == 'call':
            option_type = 'C'

        # Format the expiration date to YYMMDD
        if expiration_date != 'N/A':
            expiration_date = expiration_date[2:].replace('-', '')

        # Create the formatted symbol
        formatted_symbol = f".{root_symbol}{expiration_date}{option_type}{strike_price}"
        return formatted_symbol

# Class to analyze options and identify trading opportunities
class OptionAnalyzer:
    def __init__(self, alpaca_api, contract_info):
        self.alpaca_api = alpaca_api
        self.contract_info = contract_info
        self.opportunities = []

    # Method to calculate profit based on strike price, ask price, and stock price
    def calculate_profit(self, strike_price, ask_price, stock_price):
        return (strike_price * 100) - ((ask_price * 100) + (stock_price * 100))

    # Method to analyze available options and identify profitable opportunities
    def analyze_options(self, symbol):
        options_url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}?feed=indicative&limit=1000&type=put&strike_price_gte=50&expiration_date_gte=2024-08-05"
        current_price_url = f"https://data.alpaca.markets/v2/stocks/quotes/latest?symbols={symbol}&feed=iex"

        # Fetch options data and current prices
        options_data = self.alpaca_api.get_options_data(options_url)
        current_prices_data = self.alpaca_api.get_current_prices(current_price_url)

        # Get the current price of the stock
        current_price = current_prices_data.get('quotes', {}).get(symbol, {}).get('ap', 'N/A')
        snapshots = options_data.get('snapshots', {})

        tasks = []
        # Use a ThreadPoolExecutor to process multiple options concurrently
        with ThreadPoolExecutor(max_workers=150) as executor:
            for option_symbol, option_info in snapshots.items():
                if isinstance(option_info, dict):
                    latest_quote = option_info.get('latestQuote', {})
                    ask_price = latest_quote.get('ap', 'N/A')
                    bid_price = latest_quote.get('bp', 'N/A')

                    # Ensure prices are converted to float if they are valid
                    ask_price = float(ask_price) if ask_price != 'N/A' else 'N/A'
                    bid_price = float(bid_price) if bid_price != 'N/A' else 'N/A'

                    # Submit tasks for concurrent execution
                    tasks.append(executor.submit(self.get_contract_details_and_format, option_symbol, ask_price, bid_price))

            results = []
            for task in as_completed(tasks):
                results.append(task.result())

            # Analyze results and identify profitable opportunities
            for result in results:
                formatted_symbol, strike_price, ask_price, bid_price = result
                if strike_price is not None and ask_price != 'N/A' and ask_price > 0 and current_price != 'N/A' and float(current_price) > 0:
                    profit = self.calculate_profit(strike_price, ask_price, float(current_price))
                    if profit > 0:
                        self.opportunities.append((symbol, option_symbol, formatted_symbol, bid_price, ask_price, current_price, profit))

        return current_price

    # Method to fetch contract details and format the symbol
    def get_contract_details_and_format(self, option_symbol, ask_price, bid_price):
        contract_data = self.contract_info.get_contract_data(option_symbol)
        formatted_symbol = self.contract_info.format_symbol(contract_data)
        strike_price = float(contract_data.get('strike_price', 0))
        return formatted_symbol, strike_price, ask_price, bid_price

# Class to manage order placement and exercising options
class OrderManager:
    def __init__(self, alpaca_api):
        self.alpaca_api = alpaca_api

    # Method to place an order for a specific symbol
    def place_order(self, symbol, qty, limit_price):
        url = "https://paper-api.alpaca.markets/v2/orders"
        payload = {
            "side": "buy",
            "type": "limit",
            "time_in_force": "day",
            "symbol": str(symbol),
            "qty": str(qty),
            "limit_price": str(limit_price)
        }
        response = requests.post(url, json=payload, headers=self.alpaca_api.headers)
        return response.json()

    # Method to exercise an option for a specific symbol
    def exercise_option(self, option_symbol):
        url = f"https://paper-api.alpaca.markets/v2/positions/{option_symbol}/exercise"
        response = requests.post(url, headers=self.alpaca_api.headers)
        return response.json()

# Main class to run the trading bot
class TradingBot:
    def __init__(self, symbols):
        self.alpaca_api = AlpacaAPI("api_key", "secret_key") # <---------------------------------- Replace this with your API info
        self.contract_info = ContractInfo(self.alpaca_api)
        self.option_analyzer = OptionAnalyzer(self.alpaca_api, self.contract_info)
        self.order_manager = OrderManager(self.alpaca_api)
        self.symbols = symbols

    # Main loop to continuously analyze options and execute trades
    def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    # Analyze options for the current symbol
                    current_price = self.option_analyzer.analyze_options(symbol)

                    # Process each identified opportunity
                    for opportunity in self.option_analyzer.opportunities:
                        stock_symbol, option_symbol, formatted_symbol, bid_price, ask_price, current_price, profit = opportunity
                        
                        # Place order for the stock
                        order_response1 = self.order_manager.place_order(stock_symbol, 100, current_price)
                        # Place order for the option
                        order_response = self.order_manager.place_order(option_symbol, 1, ask_price)

                        # Wait for 30 seconds before exercising the option
                        threading.Thread(target=self.delayed_exercise, args=(option_symbol,)).start()

                        # Print the responses
                        print("Order response:")
                        print(json.dumps(order_response, indent=4))
                        print(json.dumps(order_response1, indent=4))

                    # Clear console and display current opportunities
                    self.clear_console()
                    self.display_opportunities(symbol)
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
                    continue

    # Method to clear the console output
    def clear_console(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    # Method to display the list of identified opportunities
    def display_opportunities(self, symbol):
        print(f"Symbol: {symbol}")
        print(f"{'Formatted Symbol':<25} {'Bid Price':<10} {'Ask Price':<10} {'C Price':<10} {'Profit':<10}")
        print("="*75)

        for opportunity in self.option_analyzer.opportunities:
            stock_symbol, option_symbol, formatted_symbol, bid_price, ask_price, current_price, profit = opportunity
            print(f"{formatted_symbol:<25} {bid_price:<10} {ask_price:<10} {current_price:<10} {profit:<10}")

    # Method to delay exercising the option by 30 seconds
    def delayed_exercise(self, option_symbol):
        time.sleep(30)
        exercise_response = self.order_manager.exercise_option(option_symbol)
        print("Exercise response:")
        print(json.dumps(exercise_response, indent=4))

# Entry point for the script
if __name__ == "__main__":
    symbols = ["GME"]
    bot = TradingBot(symbols)
    bot.run()
