import csv
import logging
import time
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from binance.client import Client
from binance.exceptions import BinanceAPIException
from django.db import connection
from .endpoints import *
import pandas as pd

logger = logging.getLogger(__name__)

@csrf_exempt
def index(request):
    context = {'show_download': False}
    if request.method == 'POST':
        context = {'show_download': False}
        client_name = request.POST.get('client_name')
        account_name = request.POST.get('account_name')
        category = request.POST.get('category')
        endpoint = request.POST.get('endpoint')
        # history = request.POST.get('history')
        # if history == 'history': 
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        
        account = get_account_info(account_name)

        if not account:
            context['error'] = "Account not found."
        else:
            api_key, secret_key = account[1], account[2]
            client = Client(api_key=api_key, api_secret=secret_key)

            try:
                if category == 'spot' and endpoint == 'spot_account_information':
                    # this method will store in database and will give context to pass in html page
                    context = store_spot_balances(client, account_name, context, endpoint)
                
                elif category == 'spot' and endpoint == 'spot_trade_list':
                    context = store_spot_trade_list(client, context, account_name, endpoint)

                elif category == 'spot' and endpoint == 'spot_universal_transfer_history':
                    context = store_spot_universal_transfer_history(start_date, end_date, client, account_name, endpoint, context)

                # elif category == 'spot' and endpoint == 'spot_flexible_product_position_data':
                #     context = store_spot_flexible_position_data()

                elif category == 'futures' and endpoint == 'futures_account_information_user_data':
                    context = store_futures_account_information(client, account_name, endpoint, context)

                elif category == 'futures' and endpoint == 'futures_trade_list':
                    context = store_futures_trade_list(start_date, end_date, client, account_name, endpoint, context)

                elif category == 'futures' and endpoint == 'futures_position_information':
                    context = store_futures_position_information(client, account_name, endpoint, context)

                elif category == 'futures' and endpoint == 'futures_account_balances':
                    context = store_futures_account_balances(client, account_name, endpoint, context)
                    
            except BinanceAPIException as e:
                context['error'] = str(e)
                logger.error(f"Binance API Exception: {str(e)}")

    return render(request, 'binance_app/index.html', context)


@csrf_exempt
def download_files(request):
    if request.method == 'POST':
        account_name = request.POST.get('account_name')
        endpoint = request.POST.get('endpoint')

        account = get_account_info(account_name)
        client_id = account[0]
        
        response = HttpResponse(content_type='text/csv')
        if endpoint == 'spot_account_information':
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT asset, free, locked FROM spot_data where client_id = {client_id}")
                balances = cursor.fetchall()

            response['Content-Disposition'] = 'attachment; filename="spot_data.csv"'
            writer = csv.writer(response)
            writer.writerow(['Client ID', 'Asset', 'Free', 'Locked'])

            for balance in balances:
                writer.writerow(balance)

        if endpoint == 'spot_trades_list':
            # Query the database to fetch the spot trades data
            query = f"""
                SELECT symbol, trade_id, price, qty, quote_qty, commission, commission_asset, time, is_buyer, is_maker, is_best_match
                FROM spot_trades where client_id = {client_id}
            """
            
            # Execute the query
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
            
            # Define the column names
            columns = ['Symbol', 'Trade ID', 'Price', 'Quantity', 'Quote Quantity', 'Commission', 'Commission Asset', 'Time', 'Is Buyer', 'Is Maker', 'Is Best Match']
            
            # Create a DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            # Generate Excel file
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="spot_trades.xlsx"'
            
            # Write the DataFrame to the response as an Excel file
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Spot Trades')


        if endpoint == 'spot_universal_transfer_history':
            query = f"""
                SELECT transfer_type, amount, asset, status, timestamp
                FROM universal_transfers where client_id = {client_id};
            """
            
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
            
            columns = ['Transfer Type', 'Amount', 'Asset', 'Status', 'Timestamp']
            df = pd.DataFrame(rows, columns=columns)
            
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="universal_transfers.xlsx"'
            
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Universal Transfers')

        if endpoint == 'futures_account_information_user_data':
            print('hello')
            # assets
            query = f"""
                SELECT * from futures_assets where client_id = {client_id}
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            columns = ['id', 'client_id', 'asset', 'walletBalance', 'unrealizedProfit', 'marginBalance', 'maint_margin', 'initial_margin', 'position_initial_margin', 'open_order_initial_margin', 'max_withdraw_amount', 'cross_wallet_balance', 'cross_un_pnl', 'availabee_balance', 'margin_available', 'update_time']
            df_assets = pd.DataFrame(rows, columns=columns)

            # futures
            query = f"""
                SELECT * from futures_positions where client_id = {client_id}
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall() 

            columns = ['id', 'client_id', 'symbol', 'initial_margin', 'maint_margin', 'unrealized_profit', 'position_initial_margin', 'open_order_initial_margin', 'leverage', 'isolated', 'entry_price', 'break_even_price', 'max_notional', 'position_side', 'position_amt', 'notional', 'isolated_wallet', 'update_time', 'bid_notional', 'ask_notional']
            df_positions = pd.DataFrame(rows, columns = columns)

            df_assets = df_assets.iloc[:, 1:]
            df_positions = df_positions.iloc[:, 1:]

            if 'download_assets' in request.POST:
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="futures_assets.xlsx"'
                with pd.ExcelWriter(response, engine='openpyxl') as writer:
                    df_assets.to_excel(writer, index=False)
            
            elif 'download_positions' in request.POST:
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="futures_positions.xlsx"'
                with pd.ExcelWriter(response, engine='openpyxl') as writer:
                    df_positions.to_excel(writer, index=False)

        
        if endpoint == 'futures_trade_list':
            query = f"""
                SELECT * FROM futures_trades_list where client_id = {client_id};
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            columns = ['id', 'client_id', 'symbol', 'order_id', 'side', 'price', 'qty', 'realizedPnl', 'quoteQty', 'commission', 'commissionAsset', 'time_', 'position_side', 'buyer', 'maker']
            df = pd.DataFrame(rows, columns=columns)
            new_df = df.iloc[:, 1:]
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="futures_trades_list.xlsx"'
            
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                new_df.to_excel(writer, index=False, sheet_name='Futures Trades')

        
        if endpoint == 'futures_position_information':
            query = f"""
                SELECT * FROM futures_position_info where client_id = {client_id};
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            columns = ['id', 'client_id', 'symbol', 'positionAmt', 'entryPrice', 'breakEvenPrice', 'markPrice', 'unRealizedProfit', 'liquidationPrice', 'leverage', 'maxNotionalValue', 'marginType', 'isolatedMargin', 'isAutoAddMargin', 'positionSide', 'notional', 'isolatedWallet', 'updateTime', 'isolated', 'adlQuantile']
            df = pd.DataFrame(rows, columns=columns)
            new_df = df.iloc[:, 2:]
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="futures_position_info.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                new_df.to_excel(writer, index=False, sheet_name='Futures Trades')

        
        if endpoint == "futures_account_balances":
            query = f"""
                SELECT * FROM future_account_balances where client_id = {client_id};
            """

            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            columns = ['id', 'client_id', 'accountAlias', 'asset', 'balance', 'crossWalletBalance', 'crossUnPnl', 'availableBalance', 'maxWithdrawAmount', 'marginAvailable', 'updateTime']
            df = pd.DataFrame(rows, columns=columns)
            new_df = df.iloc[:, 2:]
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="futures_acc_balances.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                new_df.to_excel(writer, index=False, sheet_name='Futures Trades')


    return response

