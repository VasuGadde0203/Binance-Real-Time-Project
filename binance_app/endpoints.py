import csv
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from django.db import connection
import requests 
from datetime import datetime, timedelta
import time
import pandas as pd
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)

BASE_URL = 'https://api.binance.com'
BASE_URL_FUTURES = 'https://fapi.binance.com'

def get_account_info(account_name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, api_key, secret_key FROM client_account_data WHERE account_name = %s", [account_name])
        return cursor.fetchone()
    

def date_to_epoch(date_str, date_format='%Y-%m-%d'):
    # Parse the date string into a datetime object
    date_obj = datetime.strptime(date_str, date_format)
    
    # Convert the datetime object to epoch time
    epoch_time = int(date_obj.timestamp())
    
    return epoch_time*1000

def sync_time(client):
    server_time = client.get_server_time()
    client_time = int(time.time() * 1000)
    time_offset = server_time['serverTime'] - client_time
    client.TIME_OFFSET = time_offset


# Spot account information
def store_spot_balances(client, account_name, context, endpoint):
    
    account = get_account_info(account_name)
    # Delete existing balances for the client before inserting new data
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM spot_data WHERE client_id = %s", [account[0]])

    # Get account information
    account_info = client.get_account()
    balances = account_info['balances']
    with connection.cursor() as cursor:
        # Delete existing balances for the client before inserting new data
        cursor.execute("DELETE FROM spot_data WHERE client_id = %s", [account[0]])
        
        for balance in balances:
            cursor.execute(
                """
                INSERT INTO spot_data (client_id, asset, free, locked)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    free = VALUES(free),
                    locked = VALUES(locked)
                """,
                (account[0], balance['asset'], balance['free'], balance['locked'])
            )
        logger.info(f"Spot Balances for {account_name} stored successfully.")
        context['data'] = balances
        context['show_download'] = True
        context['account_name'] = account_name
        context['endpoint'] = endpoint

    return context

def get_all_symbols():
    response = requests.get(f"{BASE_URL}/api/v3/exchangeInfo")
    symbols = [symbol['symbol'] for symbol in response.json()['symbols']]
    return symbols

# Spot trades list
def store_spot_trade_list(client, context, account_name, endpoint):
    try:
        symbols = get_all_symbols()
        account = get_account_info(account_name)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM spot_trades_list WHERE client_id = %s", [account[0]])

        for symbol in symbols:
            trades = client.get_my_trades(symbol=symbol)
            if trades is None or len(trades) == 0:
                continue
            
            # Insert each trade into the database
            with connection.cursor() as cursor:
                for trade in trades:
                    cursor.execute("""
                        INSERT INTO spot_trades_list (client_id, symbol, trade_id, price, qty, quote_qty, commission, commission_asset, time, is_buyer, is_maker, is_best_match)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        account[0], 
                        symbol,
                        trade['id'],
                        trade['price'],
                        trade['qty'],
                        trade['quoteQty'],
                        trade['commission'],
                        trade['commissionAsset'],
                        trade['time'],
                        trade['isBuyer'],
                        trade['isMaker'],
                        trade['isBestMatch']
                    ])
        
        context['show_download'] = True
        context['message'] = f"Trades for {account_name} stored successfully."
        context['account_name'] = account_name
        context['endpoint'] = endpoint

        
    except Exception as e:
        context['error'] = f"Failed to store trades: {str(e)}"
        logger.error(f"Failed to store trades: {str(e)}")

    return context


# Spot universal query transfer history

def store_spot_universal_transfer_history(start_date, end_date, client, account_name, context, endpoint):

    account = get_account_info(account_name)
    client_id = account[0]
    with connection.cursor() as cursor:
            cursor.execute("DELETE FROM universal_transfers WHERE client_id = %s", [client_id])

    types_list = [
        'MAIN_UMFUTURE', 'MAIN_CMFUTURE', 'MAIN_MARGIN', 'UMFUTURE_MAIN', 'UMFUTURE_MARGIN', 
        'CMFUTURE_MAIN', 'CMFUTURE_MARGIN', 'MARGIN_MAIN', 'MARGIN_UMFUTURE', 'MARGIN_CMFUTURE', 
        'MAIN_FUNDING', 'FUNDING_MAIN', 'FUNDING_UMFUTURE', 'UMFUTURE_FUNDING', 'MARGIN_FUNDING', 
        'FUNDING_MARGIN', 'FUNDING_CMFUTURE', 'CMFUTURE_FUNDING', 'MAIN_OPTION', 'OPTION_MAIN', 
        'UMFUTURE_OPTION', 'OPTION_UMFUTURE', 'MARGIN_OPTION', 'OPTION_MARGIN', 'FUNDING_OPTION', 
        'OPTION_FUNDING', 'MAIN_PORTFOLIO_MARGIN', 'PORTFOLIO_MARGIN_MAIN', 'MAIN_ISOLATED_MARGIN'
    ]

    # Loop through types and store transfer history
    for transfer_type in types_list:
        # Skip certain types based on your initial code
        if transfer_type in ['ISOLATEDMARGIN_MARGIN', 'ISOLATEDMARGIN_ISOLATEDMARGIN', 'MARGIN_ISOLATEDMARGIN', 'ISOLATED_MARGIN_MAIN', 'MAIN_ISOLATED_MARGIN']:
            continue

        transfers = get_universal_trades(client, transfer_type, start_date, end_date)
        if transfers and transfers.get('total', 0) != 0:
            with connection.cursor() as cursor:
                for transfer in transfers['rows']:
                    cursor.execute("""
                        INSERT INTO universal_transfers (transfer_type, client_id, amount, asset, status, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, [
                        transfer_type,
                        client_id, 
                        transfer['amount'],
                        transfer['asset'],
                        transfer['status'],
                        transfer['timestamp']
                    ])
    
    context['show_download'] = True
    context['message'] = "Universal transfers stored successfully."
    context['account_name'] = account_name
    context['endpoint'] = endpoint

    return context

def get_universal_trades(client, transfer_type, start_date=None, end_date=None):
    try:
        sync_time(client)

        start_time = date_to_epoch(start_date) if start_date else None
        end_time = date_to_epoch(end_date) if end_date else None

        transfers = client.query_universal_transfer_history(type=transfer_type, startTime=start_time, endTime=end_time)
        return transfers

    except Exception as e:
        logger.error(f"An error occurred while fetching universal trades: {e}")
        return None



# Spot flexible product position data
def store_spot_flexible_position_data():
    pass 


# Futures account information user data
def store_futures_account_information(client, account_name,endpoint, context):
    if context is None:
        context = {}
    acc_info = account_info_user_data(client)
    account = get_account_info(account_name)
    client_id = account[0]
    df1 = pd.DataFrame(acc_info['assets'])
    df2 = pd.DataFrame(acc_info['positions'])

    with connection.cursor() as cursor:
            cursor.execute("DELETE FROM futures_assets WHERE client_id = %s", [client_id])

    with connection.cursor() as cursor:
        for index, row in df1.iterrows():
            cursor.execute("""
                INSERT INTO futures_assets (client_id, asset, walletBalance, unrealizedProfit, marginBalance, maint_margin, initial_margin, position_initial_margin, open_order_initial_margin, max_withdraw_amount, cross_wallet_balance, cross_un_pnl, availabel_balance, margin_available, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,[
            client_id,
            row['asset'], 
            row['walletBalance'], 
            row['unrealizedProfit'], 
            row['marginBalance'],
            row['maintMargin'],
            row['initialMargin'], 
            row['positionInitialMargin'],
            row['openOrderInitialMargin'],
            row['maxWithdrawAmount'],
            row['crossWalletBalance'],
            row['crossUnPnl'], 
            row['availableBalance'], 
            row['marginAvailable'],
            row['updateTime']
        ])
            

    with connection.cursor() as cursor:
            cursor.execute("DELETE FROM futures_positions WHERE client_id = %s", [client_id])

    with connection.cursor() as cursor:
        for index, row in df2.iterrows():
            cursor.execute("""
                INSERT INTO futures_positions (client_id, symbol, initial_margin, maint_margin, unrealized_profit, position_initial_margin, open_order_initial_margin, leverage, isolated, entry_price, break_even_price, max_notional, position_side, position_amt, notional, isolated_wallet, update_time, bid_notional, ask_notional)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                client_id, 
                row['symbol'], 
                row['initialMargin'], 
                row['maintMargin'], 
                row['unrealizedProfit'], 
                row['positionInitialMargin'], 
                row['openOrderInitialMargin'], 
                row['leverage'], 
                row['isolated'], 
                row['entryPrice'], 
                row['breakEvenPrice'], 
                row['maxNotional'], 
                row['positionSide'], 
                row['positionAmt'], 
                row['notional'], 
                row['isolatedWallet'], 
                row['updateTime'], 
                row['bidNotional'], 
                row['askNotional']
            ])

    
    context['message'] = "Universal transfers stored successfully."
    context['account_name'] = account_name
    context['endpoint'] = endpoint
    context['show_assets_download'] = True
    context['show_positions_download'] = True

    return context

def account_info_user_data(client):
    # https://binance-docs.github.io/apidocs/futures/en/#account-information-v2-user_data
    try:
        acc_info = client.futures_account()
    except Exception as e:
        print(f"An error occurred: {e}")

    return acc_info


# Futures trades list
def get_all_symbols_futures():
    response = requests.get(f"{BASE_URL_FUTURES}/fapi/v1/exchangeInfo")
    symbols = [symbol['symbol'] for symbol in response.json()['symbols']]
    return symbols

def get_server_time():
    response = requests.get(f"{BASE_URL_FUTURES}/fapi/v1/time")
    server_time = response.json()['serverTime']
    return server_time

def store_futures_trade_list(start_date, end_date, client, account_name, endpoint, context):
    if context is None:
        context = {}
    account = get_account_info(account_name)
    client_id = account[0]

    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM futures_trades_list where client_id = {client_id}")

    if start_date is not None and end_date is not None:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    print(start_date)
    print(end_date)
    futures_trades_df = fetch_and_store_data(client, start_date, end_date)

    with connection.cursor() as cursor:
        for index, rows in futures_trades_df.iterrows():
            cursor.execute("""
                           INSERT INTO futures_trades_list (client_id, symbol, order_id, side, price, qty, realizedPnl, quoteQty, commission, commissionAsset, time_, position_side, buyer, maker)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           """, [
                               client_id, 
                               rows['symbol'],
                               rows['orderId'],
                               rows['side'], 
                               rows['price'], 
                               rows['qty'], 
                               rows['realizedPnl'], 
                               rows['quoteQty'], 
                               rows['commission'], 
                               rows['commissionAsset'], 
                               rows['time'], 
                               rows['positionSide'], 
                               rows['buyer'], 
                               rows['maker']
                           ])
            
    context['message'] = "Futures trades list stored successfully."
    context['account_name'] = account_name
    context['endpoint'] = endpoint
    context['show_download'] = True 
    return context


def fetch_and_store_data(client, start_time=None, end_time=None):
    symbols = get_all_symbols_futures()
    all_data = pd.DataFrame()

    if start_time is not None and end_time is not None:
        while start_time < end_time:
            next_end_time = min(start_time + timedelta(7), end_time)
            if next_end_time > end_time:
                next_end_time = end_time

            start_epoch = int(start_time.timestamp() * 1000)
            end_epoch = int(next_end_time.timestamp() * 1000)

            for symbol in symbols:
                acc_trade_list = acc_trade_list_user_data(client, symbol, start_epoch, end_epoch)
                if acc_trade_list is None or not acc_trade_list:
                    continue 
                df = pd.DataFrame(acc_trade_list)
                all_data = pd.concat([all_data, df], ignore_index=True)
                time.sleep(0.1)

            start_time = next_end_time

    if not all_data.empty:
        all_data['time'] = pd.to_datetime(all_data['time'], unit='ms')
        return all_data

def acc_trade_list_user_data(client, symbol, start_time=None, end_time=None):
    acc_trade = None 
    try:
        for attempt in range(5):     # Try up to 5 times
            try: 
                acc_trade = client.futures_account_trades(symbol=symbol, startTime = start_time, endTime= end_time, recvWindow=10000)
                break 
            except RequestException as e:
                print(f"Attempt { attempt + 1} failed: {e}")
                time.sleep(2)

    except Exception as e:
        print(f"An error occurred: {e}")

    return acc_trade
    



# Futuers position information 
def store_futures_position_information(client, account_name, endpoint, context):
    if context is None:
        context = {}
    account = get_account_info(account_name)
    client_id = account[0]

    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM futures_position_info where client_id = {client_id}")

    try:
        res = client.get_server_time()
        client.timestamp_offset = res['serverTime'] - int(time.time()*1000)
        position_info = client.futures_position_information()

    except Exception as e:
        print(f"An error occurred: {e}")
    
    df = pd.DataFrame(position_info)

    with connection.cursor() as cursor:
        for index, rows in df.iterrows():
            cursor.execute("""
                INSERT INTO futures_position_info (client_id, symbol, positionAmt, entryPrice, breakEvenPrice, markPrice, unRealizedProfit, liquidationPrice, leverage, maxNotionalValue, marginType, isolatedMargin, isAutoAddMargin, positionSide, notional, isolatedWallet, updateTime, isolated, adlQuantile)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                client_id, 
                rows['symbol'], 
                rows['positionAmt'],
                rows['entryPrice'], 
                rows['breakEvenPrice'],
                rows['markPrice'],
                rows['unRealizedProfit'],
                rows['liquidationPrice'], 
                rows['leverage'], 
                rows['maxNotionalValue'], 
                rows['marginType'],
                rows['isolatedMargin'], 
                rows['isAutoAddMargin'], 
                rows['positionSide'],
                rows['notional'],
                rows['isolatedWallet'],
                rows['updateTime'],
                rows['isolated'],
                rows['adlQuantile']
            ])
    context['message'] = "Futures position information stored successfully."
    context['account_name'] = account_name
    context['endpoint'] = endpoint
    context['show_download'] = True
    return context 


# Futures account balances 
def store_futures_account_balances(client, account_name, endpoint, context): 
    if context is None:
        context = {}

    account = get_account_info(account_name)
    client_id = account[0]

    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM future_account_balances where client_id = {client_id}")

    try:
        res = client.get_server_time()
        client.timestamp_offset = res['serverTime'] - int(time.time()*1000)
        futures_balance = client.futures_account_balance()

    except Exception as e:
        print(f"An error occurred: {e}")

    df = pd.DataFrame(futures_balance)

    with connection.cursor() as cursor:
        for index, rows in df.iterrows():
            cursor.execute("""
                INSERT INTO future_account_balances (client_id, accountAlias, asset, balance, crossWalletBalance, crossUnPnl, availableBalance, maxWithdrawAmount, marginAvailable, updateTime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            client_id, 
            rows['accountAlias'], 
            rows['asset'], 
            rows['balance'], 
            rows['crossWalletBalance'], 
            rows['crossUnPnl'], 
            rows['availableBalance'], 
            rows['maxWithdrawAmount'], 
            rows['marginAvailable'], 
            rows['updateTime']
        ])
    
    context['message'] = "Futures balances stored successfully."
    context['account_name'] = account_name
    context['endpoint'] = endpoint
    context['show_download'] = True
    return context 



def download_balances_as_csv():
    # Implement CSV downloading logic here if needed.
    pass
