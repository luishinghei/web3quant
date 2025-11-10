"""
Roostoo Mock Exchange Public API - Python Client
------------------------------------------------
This script demonstrates how to interact with the Roostoo Mock Exchange API.
It supports both public and signed endpoints with HMAC SHA256 authentication.

Base URL: https://mock-api.roostoo.com
"""

import requests
import time
import hmac
import hashlib
from dotenv import load_dotenv
import os
from quanttrading.log import init_logger
from quanttrading import tg
import time
from quanttrading.binance_fetcher import BinanceFetcher


logger = init_logger('roostoo')

# --- API Configuration ---
load_dotenv()
BASE_URL = "https://mock-api.roostoo.com"
API_KEY = os.getenv('ROOSTOO_API_KEY')
SECRET_KEY = os.getenv('ROOSTOO_API_SECRET')
MIN_ORDER_USD = 2.0


# ------------------------------
# Utility Functions
# ------------------------------

def _get_timestamp():
    """Return a 13-digit millisecond timestamp as string."""
    return str(int(time.time() * 1000))


def _get_signed_headers(payload: dict = {}):
    """
    Generate signed headers and totalParams for RCL_TopLevelCheck endpoints.
    """
    payload['timestamp'] = _get_timestamp()
    sorted_keys = sorted(payload.keys())
    total_params = "&".join(f"{k}={payload[k]}" for k in sorted_keys)

    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        total_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'RST-API-KEY': API_KEY,
        'MSG-SIGNATURE': signature
    }

    return headers, payload, total_params


# ------------------------------
# Public Endpoints
# ------------------------------

def check_server_time():
    """Check API server time."""
    url = f"{BASE_URL}/v3/serverTime"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking server time: {e}")
        return None


def get_exchange_info():
    """Get exchange trading pairs and info."""
    url = f"{BASE_URL}/v3/exchangeInfo"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting exchange info: {e}")
        return None


def get_ticker(pair=None):
    """Get ticker for one or all pairs."""
    url = f"{BASE_URL}/v3/ticker"
    params = {'timestamp': _get_timestamp()}
    if pair:
        params['pair'] = pair
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting ticker: {e}")
        return None


# ------------------------------
# Signed Endpoints
# ------------------------------

def get_balance():
    """Get wallet balances (RCL_TopLevelCheck)."""
    url = f"{BASE_URL}/v3/balance"
    headers, payload, _ = _get_signed_headers({})
    try:
        res = requests.get(url, headers=headers, params=payload)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting balance: {e}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        return None


def get_pending_count():
    """Get total pending order count."""
    url = f"{BASE_URL}/v3/pending_count"
    headers, payload, _ = _get_signed_headers({})
    try:
        res = requests.get(url, headers=headers, params=payload)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting pending count: {e}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        return None


def place_order(pair_or_coin, side, quantity, price=None, order_type=None):
    """
    Place a LIMIT or MARKET order.
    """
    url = f"{BASE_URL}/v3/place_order"
    pair = f"{pair_or_coin}/USD" if "/" not in pair_or_coin else pair_or_coin

    if order_type is None:
        order_type = "LIMIT" if price is not None else "MARKET"

    if order_type == 'LIMIT' and price is None:
        logger.error("Error: LIMIT orders require 'price'.")
        tg.send_message(f"Error: LIMIT orders require 'price'.")
        return None

    payload = {
        'pair': pair,
        'side': side.upper(),
        'type': order_type.upper(),
        'quantity': str(quantity)
    }
    if order_type == 'LIMIT':
        payload['price'] = str(price)

    headers, _, total_params = _get_signed_headers(payload)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'

    try:
        res = requests.post(url, headers=headers, data=total_params)
        res.raise_for_status()
        logger.info(f"Order placed: {res.json()}")
        # tg.send_message(f"Order placed: {res.json()}")
        return res.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error placing order: {e}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        # tg.send_message(f"Error placing order: {e}")
        return None


def query_order(order_id=None, pair=None, pending_only=None):
    """Query order history or pending orders."""
    url = f"{BASE_URL}/v3/query_order"
    payload = {}
    if order_id:
        payload['order_id'] = str(order_id)
    elif pair:
        payload['pair'] = pair
        if pending_only is not None:
            payload['pending_only'] = 'TRUE' if pending_only else 'FALSE'

    headers, _, total_params = _get_signed_headers(payload)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'

    try:
        res = requests.post(url, headers=headers, data=total_params)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying order: {e}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        return None


def cancel_order(order_id=None, pair=None):
    """Cancel specific or all pending orders."""
    url = f"{BASE_URL}/v3/cancel_order"
    payload = {}
    if order_id:
        payload['order_id'] = str(order_id)
    elif pair:
        payload['pair'] = pair

    headers, _, total_params = _get_signed_headers(payload)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'

    try:
        res = requests.post(url, headers=headers, data=total_params)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error canceling order: {e}")
        print(f"Response text: {e.response.text if e.response else 'N/A'}")
        return None


def get_current_postions() -> dict[str, float]:
    data = get_balance()

    spot_wallet = data['SpotWallet']
    positions = {}
    # {'Success': True, 'ErrMsg': '', 'SpotWallet': {'ETH': {'Free': 0.01, 'Lock': 0}, 'USD': {'Free': 49966.14, 'Lock': 0}}, 'MarginWallet': {}}
    for coin, data in spot_wallet.items():
        # if coin == 'USD':
        #     continue
        positions[coin] = data['Free']
    return positions


def get_free_usd() -> float:
    data = get_balance()
    
    spot_wallet = data['SpotWallet']
    return spot_wallet['USD']['Free']


def trade(amount_by_symbol: dict[str, float], binance_fetcher: BinanceFetcher, last_prices: dict[str, float] | None = None) -> tuple[list[dict], list[dict]]:
    has_trade = False
    success_trades = []
    error_trades = []
    
    for symbol, amount in amount_by_symbol.items():
        if amount == 0.0:
            continue
        if symbol == 'USD':
            continue

        # Build pair and pre-check minimal USD order value when price is available
        pair = f"{symbol}/USD" if "/" not in symbol else symbol
        # Use provided last_prices if available, otherwise fetch
        if last_prices is not None and symbol in last_prices:
            last_price = last_prices[symbol]
        else:
            last_price = binance_fetcher.fetch_last_price(symbol)
        if last_price is not None:
            usd_value = abs(amount) * last_price
            if usd_value < MIN_ORDER_USD:
                msg = "[TRADE SKIPPED] \n"
                msg += f"Reason: order value ${usd_value:.6f} < ${MIN_ORDER_USD:.6f} \n"
                msg += f"Symbol: {pair} \n"
                msg += f"Amount: {abs(amount)} @ ~{last_price} \n"
                tg.send_message(msg)
                logger.info(f"Skip {pair} amount {amount} below min USD {MIN_ORDER_USD}")
                continue
        
        # Place order based on amount sign
        if amount > 0:
            response = place_order(symbol, 'BUY', amount)
            has_trade = True
        elif amount < 0:
            response = place_order(symbol, 'SELL', -amount)
            has_trade = True
        else:
            continue
        
        # # Check if order placement was successful
        # if response is None:
        #     logger.error(f"Failed to place order for {symbol}")
        #     continue
        # {'Success': True, 'ErrMsg': '', 'OrderDetail': {'Pair': 'ETH/USD', 'OrderID': 2344053, 'Status': 'FILLED', 'Role': 'TAKER', 'ServerTimeUsage': 0.008577462, 'CreateTimestamp': 1762438851040, 'FinishTimestamp': 1762438851048, 'Side': 'SELL', 'Type': 'MARKET', 'StopType': 'GTC', 'Price': 3367.13, 'Quantity': 0.01, 'FilledQuantity': 0.01, 'FilledAverPrice': 3367.13, 'CoinChange': 0.01, 'UnitChange': 33.6713, 'CommissionCoin': 'USD', 'CommissionChargeValue': 0.033671, 'CommissionPercent': 0.001, 'OrderWalletType': 'SPOT', 'OrderSource': 'PUBLIC_API'}}
        
        if response['Success']:
            msg = '[TRADE SUCCESS] \n'
            msg += f'Status: {response['OrderDetail']['Status']} \n'
            msg += f'Symbol: {response['OrderDetail']['Pair']} \n'
            msg += f'Amount: {response['OrderDetail']['Quantity']} \n'
            msg += f'Side: {response['OrderDetail']['Side']} \n'
            msg += f'Type: {response['OrderDetail']['Type']} \n'
            msg += f'Price: {response['OrderDetail']['Price']} \n'
            tg.send_message(msg)
            success_trades.append(response)
        else:
            msg = '[TRADE ERROR] \n'
            msg += f'Status: {response['ErrMsg']} \n'
            tg.send_message(msg)
            error_trades.append(response)
        time.sleep(2)
    if not has_trade:
        return success_trades, error_trades

    pending_count = get_pending_count()
    if pending_count['ErrMsg'] == 'no pending order under this account':
        logger.info("No pending orders")
        tg.send_message("No pending orders")
    else:
        logger.error("Pending orders found")
        tg.send_message("Pending orders found")

    return success_trades, error_trades

# ------------------------------
# Quick Demo Section
# ------------------------------
if __name__ == "__main__":
    print("\n--- Checking Server Time ---")
    print(check_server_time())

    print("\n--- Getting Exchange Info ---")
    info = get_exchange_info()
    if info:
        print(f"Available Pairs: {list(info.get('TradePairs', {}).keys())}")

    print("\n--- Getting Market Ticker (BTC/USD) ---")
    ticker = get_ticker("BTC/USD")
    if ticker:
        print(ticker.get("Data", {}).get("BTC/USD", {}))

    print("\n--- Getting Account Balance ---")
    print(get_balance())

    print("\n--- Checking Pending Orders ---")
    print(get_pending_count())

    # Uncomment these to test trading actions:
    # print(place_order("BTC", "BUY", 0.01, price=95000))  # LIMIT
    print(place_order("BNB/USD", "BUY", 1))      
    print(place_order("BNB/USD", "SELL", 1))             # MARKET       
    print(query_order(pair="BNB/USD", pending_only=False))
    # print(cancel_order(pair="BNB/USD"))
