import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import ta
import telegram
import asyncio
import time

# Set up the exchange and pair
exchange = ccxt.binance()
symbol = 'ETH/USDT'

# Set up the candle timeframe
timeframe = '15m'

# Set up the Telegram bot
bot_token = '6207709237:AAEGT3X3X-JMkETaSa6oQw14cJPo0qsonrg'
chat_id = '-1001501848303'


async def send_telegram_message(message):
    bot = telegram.Bot(token=bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except telegram.error.TelegramError as e:
        print(f"Error sending message: {e}")

fecha_log = datetime.now().strftime("%d-%m-%Y %H:%M")

with open(f"WarrenBotLOG{fecha_log}.txt", "w") as f:
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
        # Initial message
        intro = f"🤖 Warren Bot v1.0 - Running 🚀\nInitial Balance: {initial_account_balance} USDT\n% of K used for orders: {(perc_capital*100)}\n🔵 15 minutes timeframe\n"
        f.write(intro)
        await send_telegram_message(intro)
        print(intro)
        buy_signal = False
        sell_signal = True
        while True:
            # Fetch the last 500 candles
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)

            # Convert the data to a pandas DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Calculate the MACD indicator
            df['MACD'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
            df['Signal_line'] = df['MACD'].ewm(span=9, adjust=False).mean()

            # Calculate the ADX indicator
            df['TR1'] = abs(df['high'] - df['low'])
            df['TR2'] = abs(df['high'] - df['close'].shift())
            df['TR3'] = abs(df['low'] - df['close'].shift())
            df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
            df['DMplus'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), df['high'] - df['high'].shift(), 0)
            df['DMminus'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), df['low'].shift() - df['low'], 0)
            df['DIplus'] = df['DMplus'].ewm(span=14, adjust=False).mean()
            df['DIminus'] = df['DMminus'].ewm(span=14, adjust=False).mean()
            df['DIdiff'] = df['DIplus'] - df['DIminus']
            df['DIsum'] = df['DIplus'] + df['DIminus']
            df['DX'] = 100 * (abs(df['DIdiff']/df['DIsum']))
            df['ADX'] = df['DX'].ewm(span=14, adjust=False).mean()

            # Calculate the RSI indicator
            df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=11).rsi()

            # Calculate the accumulation/distribution line
            df['ADL'] = (df['close'] - df['low']) - (df['high'] - df['close']) / (df['high'] - df['low'])

            # Calculate the moving average convergence/divergence
            df['MACD_line'] = (df['close'].ewm(span=12, adjust=False).mean()) - (df['close'].ewm(span=26, adjust=False).mean())

            # Generate buy/sell signals based on MACD, ADX, RSI, ADL and MACD_line
            df['signal'] = 0.0
            df['signal'] = np.where(((df['MACD'] > df['Signal_line']) & (df['ADX'] > 25) & (df['RSI'] > 70) & (
                        df['ADL'] > 0) & (df['MACD_line'] > 0)), 1.0, 0.0)
            df['signal'] = np.where(((df['MACD'] < df['Signal_line']) & (df['ADX'] > 25) & (df['RSI'] < 30) & (
                        df['ADL'] < 0) & (df['MACD_line'] < 0)), -1.0, df['signal'])

            # Calculate the positions based on the signals
            df['position'] = df['signal'].diff()

            # Skip the current candle if it has already started
            current_time = datetime.now()
            current_candle_start_time = current_time.replace(minute=(current_time.minute // 1) * 1, second=0,
                                                             microsecond=0)
            if df.index[-1] < current_candle_start_time:
                continue

            ticker_symbol = exchange.fetch_ticker(symbol)
            last_price = ticker_symbol['last']  # Update the last_price variable

            # Check the last row of the DataFrame for buy/sell signals and prices
            for i, row in df.tail(1).iterrows():
                # Check for buy signal
                if row['position'] == 1 and buy_signal == False:
                    current_time_buy = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    buy_price = last_price
                    buy_balance = account_balance * perc_capital
                    position = buy_balance / buy_price
                    account_balance = account_balance - (buy_price * position)
                    message = f"🔵 📈 BUY {buy_balance:.2f} in {symbol} at {current_time_buy} price: {buy_price}\nAccount balance: {account_balance:.2f}\n"
                    await send_telegram_message(message)
                    print(message)
                    f.write(message)
                    buy_signal = True
                    sell_signal = False
                # Check for sell signal
                elif row['position'] == -1 and sell_signal == False:
                    current_time_sell = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    sell_price = last_price
                    profit = (sell_price - buy_price) / buy_price * 100
                    profit_list.append((current_time_sell, profit))
                    account_balance = account_balance + (sell_price * position) - (buy_price * position) + (
                    (buy_balance + (buy_balance * (profit / 100))))
                    message = f"🔵 📉 SELL {position:.2f} {symbol} at {current_time_sell} price: {sell_price}, profit: {profit:.2f}%\nAccount balance: {account_balance:.2f}\n"
                    message2 = f"🔵 Total Profit/Loss (%): {sum(tup[1] for tup in profit_list):.2f}\n"
                    await send_telegram_message(message)
                    await send_telegram_message(message2)
                    print(message)
                    f.write(message)
                    f.write(message2)
                    position = 0.0
                    sell_signal = True
                    buy_signal = False

            # Wait for the next candle to form
            current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            message = "Waiting for next candle at {}".format(current_time)
            print("--------------------------------------------------------------------")
            print(message)
            print(df.tail(1))
            print(f"{symbol} last price: {last_price}")
            print(f"Profit/Loss (%): {sum(tup[1] for tup in profit_list):.2f}")
            print("--------------------------------------------------------------------")
            time.sleep(30)  # Wait for 30 seconds before fetching the next set of candles

    asyncio.run(run_bot())
