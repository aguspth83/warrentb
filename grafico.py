import ccxt
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from datetime import datetime, timedelta
import numpy as np


def grafico(crypto, timeframe, csv):

    # Crea una instancia del intercambio Binance
    exchange = ccxt.binance()

    # Define los parámetros para la descarga de datos
    symbol = crypto
    timeframe = timeframe   # Intervalo de tiempo de 4 horas
    limit = 700         # Número máximo de velas a descargar para una semana (42 velas de 4 horas en una semana)

    # Calcula la fecha de inicio y final para el período deseado (1 semana desde hoy)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Descarga los datos del par ETH/USDT en un DataFrame de Pandas
    ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])

    # Convierte el timestamp a un objeto datetime
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')

    # Filtra los datos para el período deseado
    df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    # Filtra los datos para obtener solo las señales de compra y venta
    signals = pd.read_csv(csv)
    signals = signals[signals['Symbol'] == symbol]
    signals['Date'] = pd.to_datetime(signals['Date'], format='%d-%m-%Y %H:%M:%S')
    signals = signals[(signals['Date'] >= start_date) & (signals['Date'] <= end_date)]

    # Crea una figura de velas utilizando Plotly
    fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                                          open=df['Open'],
                                          high=df['High'],
                                          low=df['Low'],
                                          close=df['Close'],
                                          increasing_line_color='green',
                                          decreasing_line_color='red')])

    # Añade las señales de compra y venta al gráfico
    for index, row in signals.iterrows():
        if row['Type'] == 'Buy':
            fig.add_annotation(x=row['Date'], y=row['Price'], text='<b>Buy</b>', showarrow=True, arrowhead=1, arrowsize=2, font=dict(color='green'))
        elif row['Type'] == 'Sell':
            fig.add_annotation(x=row['Date'], y=row['Price'], text='<b>Sell</b>', showarrow=True, arrowhead=1, arrowsize=2, font=dict(color='red'))

    # Define el diseño del gráfico con una resolución de 1920x1080
    fig.update_layout(title=f'Gráfico de velas para {symbol}',
                      xaxis_title='Fecha',
                      yaxis_title='Precio',
                      yaxis_tickprefix='$',
                      width=1920,
                      height=1080)

    # Guarda el gráfico en un archivo JPEG con una calidad del 95%
    file_name = f'velas.jpg'
    pio.write_image(fig, file_name, format='jpeg')

    # Filtra los datos para obtener solo las señales de venta
    sell_signals = signals[signals['Type'] == 'Sell']

    # Filtra los datos para la última semana
    last_week = sell_signals[sell_signals['Date'] >= start_date]

    # Calcula el profit de cada operación
    last_week['Profit'] = last_week['Profit/Loss'].apply(lambda x: float(str(x).strip('%')) / 100)
    last_week['Profit_USD'] = last_week['Amount'] * last_week['Price'] * last_week['Profit']
    last_week = last_week.sort_values('Date')

    # Crea un gráfico de barras que muestre el profit de cada operación
    fig2 = go.Figure(data=[go.Bar(x=last_week['Date'],
                                  y=last_week['Profit_USD'])])

    # Define el diseño del gráfico con una resolución de 1920x1080
    fig2.update_layout(title=f'Profit de las operaciones de venta en la última semana {symbol}',
                       xaxis_title='Fecha',
                       yaxis_title='Profit en USD',
                       yaxis_tickprefix='$',
                       width=1920,
                       height=1080)

    # Guarda el gráfico en un archivo JPEG con una calidad del 95%
    file_name2 = f'profit_chart.jpg'
    pio.write_image(fig2, file_name2, format='jpeg')

    print(last_week)

    # Calcula el profit acumulado de los últimos 7 días
    daily_pnl = []
    date_range = pd.date_range(start=start_date, end=end_date)
    for date in date_range:
        day_signals = sell_signals[sell_signals['Date'].dt.date == date.date()]
        if not day_signals.empty:
            day_profit = last_week['Profit_USD'].sum()
            daily_pnl.append(day_profit)
        else:
            daily_pnl.append(0)

    # Calcula el profit acumulado de los últimos 7 días
    cumulative_pnl = np.cumsum(daily_pnl)

    # Crea un gráfico de línea que muestre el profit diario de los últimos 30 días
    fig3 = go.Figure(data=[go.Scatter(x=date_range,
                                      y=daily_pnl)])

    # Define el diseño del gráfico con una resolución de 1920x1080
    fig3.update_layout(title=f'PNL diario de los últimos 7 días {symbol}',
                       xaxis_title='Fecha',
                       yaxis_title='PNL diario en USD',
                       yaxis_tickprefix='$',
                       width=1920,
                       height=1080)

    # Guarda el gráfico en un archivo JPEG con una calidad del 95%
    file_name3 = f'daily_pnl.jpg'
    pio.write_image(fig3, file_name3, format='jpeg')

