import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class FractalAggressiveV14(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'

    # --- PARÁMETROS OPTIMIZABLES (CEREBRO BTC) ---
    btc_adx_threshold = IntParameter(20, 50, default=30, space='buy')
    btc_rsi_threshold = IntParameter(50, 80, default=65, space='buy')
    
    # --- PARÁMETROS OPTIMIZABLES (MODOS ALCISTAS) ---
    # Modo 1: Explorador
    b1_rsi = IntParameter(40, 70, default=56, space='buy')
    b1_adx = IntParameter(20, 50, default=40, space='buy')
    b1_obv = DecimalParameter(1.0, 1.1, default=1.03, space='buy')

    # Modo 2: Locomotora
    b2_rsi = IntParameter(40, 75, default=60, space='buy')
    b2_adx = IntParameter(20, 55, default=40, space='buy')
    b2_obv = DecimalParameter(1.1, 1.5, default=1.30, space='buy')

    # Modo 3: Francotirador
    b3_rsi = IntParameter(30, 60, default=45, space='buy')
    b3_adx = IntParameter(20, 50, default=35, space='buy')
    b3_obv = DecimalParameter(1.0, 1.2, default=1.05, space='buy')

    # --- CONFIGURACIÓN DE SALIDA AGRESIVA ---
    # Dejamos que Hyperopt también optimice el ROI para no cortar las ganancias
    minimal_roi = {
        "0": 0.30,      # Esperamos un 30% inicial
        "60": 0.10,     # A la hora bajamos pretensiones
        "150": 0.03,    
        "300": 0        # Salida por tiempo
    }

    stoploss = -0.10    # Stoploss más amplio (10%) para aguantar la volatilidad del Bull
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    def informative_pairs(self):
        return [("BTC/USDT", "5m")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)

        if self.dp:
            btc_df = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe="5m")
            btc_df['rsi_btc'] = ta.RSI(btc_df, timeperiod=14)
            btc_df['adx_btc'] = ta.ADX(btc_df, timeperiod=14)
            btc_df['ema_200_btc'] = ta.EMA(btc_df, timeperiod=200)
            dataframe = pd.merge(dataframe, btc_df[['date', 'rsi_btc', 'adx_btc', 'ema_200_btc', 'close']], 
                                 on='date', how='left', suffixes=('', '_btc'))
            dataframe.ffill(inplace=True)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if 'close_btc' in dataframe.columns:
            locomotora = (dataframe['adx_btc'] > self.btc_adx_threshold.value) & (dataframe['rsi_btc'] > self.btc_rsi_threshold.value)
            francotirador = (dataframe['rsi_btc'] < 45)
            explorador = (dataframe['adx_btc'] <= self.btc_adx_threshold.value)

            base_filter = (dataframe['close_btc'] > dataframe['ema_200_btc']) & (dataframe['close'] > dataframe['ema_200'])

            c_explo = base_filter & explorador & (dataframe['rsi'] < self.b1_rsi.value) & (dataframe['adx'] > self.b1_adx.value) & (dataframe['obv'] > dataframe['obv_ema'] * self.b1_obv.value)
            c_loco = base_filter & locomotora & (dataframe['rsi'] < self.b2_rsi.value) & (dataframe['adx'] > self.b2_adx.value) & (dataframe['obv'] > dataframe['obv_ema'] * self.b2_obv.value)
            c_franco = base_filter & francotirador & (dataframe['rsi'] < self.b3_rsi.value) & (dataframe['adx'] > self.b3_adx.value) & (dataframe['obv'] > dataframe['obv_ema'] * self.b3_obv.value)

            dataframe.loc[c_explo | c_loco | c_franco, 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > 85), 'exit_long'] = 1 # Salida más arriba para dejar correr
        return dataframe