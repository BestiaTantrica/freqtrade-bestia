import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class FractalAlcistaV18(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'

    # --- PARÁMETROS OPTIMIZADOS ---
    c1_rsi = IntParameter(50, 60, default=55, space='buy')
    c2_adx = IntParameter(20, 40, default=30, space='buy')
    c3_rsi = IntParameter(65, 80, default=70, space='buy')
    sell_rsi = IntParameter(75, 95, default=85, space='sell')

    # --- GESTIÓN DE RIESGO AVANZADA ---
    stoploss = -0.08  # Stop inicial de seguridad

    # TRAILING STOP: El secreto para proteger el profit
    trailing_stop = True
    trailing_stop_positive = 0.02     # Se activa cuando hay 2% de ganancia
    trailing_stop_positive_offset = 0.03 # Mantiene el stop a 3% de distancia del pico
    trailing_only_offset_is_reached = True

    minimal_roi = {
        "0": 0.15,      
        "60": 0.08,     
        "180": 0.04,    
        "360": 0
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, window=14)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sobre_ema200 = dataframe['close'] > dataframe['ema200']
        con_volumen = dataframe['volume'] > dataframe['volume_mean']

        dataframe.loc[sobre_ema200 & con_volumen & (dataframe['rsi'] > self.c1_rsi.value), ['enter_long', 'enter_tag']] = (1, 'alcista_INICIO_c1')
        dataframe.loc[sobre_ema200 & (dataframe['adx'] > self.c2_adx.value) & (dataframe['rsi'] > 58), ['enter_long', 'enter_tag']] = (1, 'alcista_FUERTE_c2')
        dataframe.loc[sobre_ema200 & (dataframe['rsi'] > self.c3_rsi.value) & (dataframe['adx'] > 35), ['enter_long', 'enter_tag']] = (1, 'alcista_ROCKET_c3')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > self.sell_rsi.value), 'exit_long'] = 1
        return dataframe