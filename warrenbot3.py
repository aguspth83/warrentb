"""
17-04-23
SE AGREGA EN ESTA VERSIÓN:
- TRAILING STOPLOSS
- BOT SLEEP AL PRIMER STOPLOSS DE 1 %
- SE AGREGA CSV
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import telegram
import asyncio
import time
import csv
import os

# Set up the exchange and pair
exchange = ccxt.binance()
symbol = 'ETH/USDT'

# Set up the candle timeframe
timeframe = '15m'

# Set up the Telegram bot
bot_token = '6207709237:AAEGT3X3X-JMkETaSa6oQw14cJPo0qsonrg'
chat_id = '-1001501848303'

csv_filename = 'trading_data.csv'
csv_headers = ['Type', 'Amount', 'Symbol', 'Price', 'Fee', 'Profit/Loss', 'Date']
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)

async def send_telegram_message(message):
    bot = telegram.Bot(token=bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except telegram.error.TelegramError as e:
        print(f"Error sending message: {e}")

# Infinite loop to continuously fetch live data and generate signals
async def run_bot():
    # Set up variables for tracking positions
    initial_account_balance = 1000  # initial account balance
    account_balance = 1000  # updated account balance
    perc_capital = 0.8  # percentage of balance used for orders
    buy_balance = 0
    buy_price = 0.0
    sell_price = 0.0
    position = 0.0
    profit_list = []
    stoploss_percent = 0.01  # set the stoploss in percentage
    t_stoploss_percent = 0.002
    fee_perc = 0.001 # Binance transaction fee
    fee_buy = 0.0
    fee_sell = 0.0
    stoploss_count = 0

    # Initial message
    intro = f"🤖 Warren Bot v3.0 - Running 🚀\nInitial Balance: {initial_account_balance} USDT\n% of K used for orders: {(perc_capital*100)}\n5 minute timeframe\nStoploss: {stoploss_percent*100}%\nBinance fee: {fee_perc*100}%\n"
    await send_telegram_message(intro)
    print(intro)
    buy_signal = False
    sell_signal = True

    def write_to_csv(data):
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)

    while True:
        # Fetch the last 500 candles
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)

        # Convert the data to a pandas DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Calculate the Bollinger Bands
        df['Rolling_Mean'] = df['close'].rolling(window=20).mean()
        df['Rolling_Std'] = df['close'].rolling(window=20).std()
        df['Upper_Band'] = df['Rolling_Mean'] + (2 * df['Rolling_Std'])
        df['Middle_Band'] = df['Rolling_Mean']
        df['Lower_Band'] = df['Rolling_Mean'] - (2 * df['Rolling_Std'])

        # Generate buy/sell signals based on Bollinger bands
        df['signal'] = np.where((df['close'] < df['Lower_Band']), 1.0, 0.0)
        df['signal'] = np.where((df['close'] > df['Upper_Band']), -1.0, df['signal'])

        ticker_symbol = exchange.fetch_ticker(symbol)
        last_price = ticker_symbol['last']  # Update the last_price variable

        # Define a variable to keep track of the highest price since the sell signal appeared
        highest_price = 0

        # Check the last row of the DataFrame for buy/sell signals and prices
        for i, row in df.tail(1).iterrows():
            # Check for buy signal
            if row['signal'] == 1 and buy_signal == False:
                current_time_buy = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                buy_price = last_price
                buy_balance = account_balance * perc_capital
                position = buy_balance / buy_price
                fee_buy = buy_balance * fee_perc
                account_balance = account_balance - (buy_price * position) - (fee_buy)
                message = f"🔵 📈 BUY {buy_balance:.2f} in {symbol} at {current_time_buy} price: {buy_price}\nBinance Fee: {fee_buy:.2f}\nETH balance: {position:.2f}\nAccount balance: {account_balance:.2f}\n"
                write_to_csv(['Buy', buy_balance, symbol, buy_price, fee_buy,'', current_time_buy])
                await send_telegram_message(message)
                print(message)
                buy_signal = True
                sell_signal = False
                # Reset the highest price
                highest_price = 0
            # Check for sell signal and trailing stop loss
            elif row['signal'] == -1 and sell_signal == False and row['close'] >= (
                    1 - t_stoploss_percent) * highest_price and (sell_price - buy_price) / buy_price >= 0.003:
                current_time_sell = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                sell_price = last_price
                fee_sell = (sell_price * position) * fee_perc
                profit = (sell_price - buy_price) / buy_price * 100
                profit_list.append((current_time_sell, profit))
                account_balance = account_balance + (sell_price * position) - (fee_sell)
                message = f"🟢 📉 SELL {position:.2f} {symbol} at {current_time_sell} price: {sell_price}\nProfit: {profit:.2f}%\nBinance Fee: {fee_sell:.2f}\nETH balance: 0\nAccount balance: {account_balance:.2f}\nTotal Profit/Loss (%): {(((account_balance / initial_account_balance) - 1) * 100):.2f}\n"
                write_to_csv(['Sell', position, symbol, sell_price, fee_sell, profit, current_time_sell])
                await send_telegram_message(message)
                print(message)
                position = 0.0
                stoploss_count = 0
                sell_signal = True
            # Check for stop loss at 1% below buying price
            elif (row['close'] < (1 - stoploss_percent) * buy_price) and sell_signal == False:
                current_time_sell = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                sell_price = last_price
                fee_sell = (sell_price * position) * fee_perc
                profit = (sell_price - buy_price) / buy_price * 100
                profit_list.append((current_time_sell, profit))
                account_balance = account_balance + (sell_price * position) - (fee_sell)
                message = f"🔴 📉 SELL STOPLOSS 1% below buying price {position:.2f} {symbol} at {current_time_sell} price: {sell_price}\nProfit: {profit:.2f}%\nBinance Fee: {fee_sell:.2f}\nETH balance: 0\nAccount balance: {account_balance:.2f}\nTotal Profit/Loss (%): {(((account_balance / initial_account_balance) - 1) * 100):.2f}\n"
                write_to_csv(['Sell', position, symbol, sell_price, fee_sell, profit, current_time_sell])
                await send_telegram_message(message)
                print(message)
                position = 0.0
                stoploss_count = 0
                sell_signal = True
            # Update the highest price
            if row['close'] > highest_price:
                highest_price = row['close']
                print(highest_price)

        # Wait for the next candle to form
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        message = "Waiting for next candle at {}".format(current_time)
        print("--------------------------------------------------------------------")
        print(message)
        print(df.tail(1))
        print(f"{symbol} last price: {last_price}")
        print(f"Profit/Loss (%): {(((initial_account_balance / account_balance) - 1) * 100):.2f}\n")
        print("--------------------------------------------------------------------")
        time.sleep(10)  # Wait for 10 seconds before fetching the next set of candles

asyncio.run(run_bot())