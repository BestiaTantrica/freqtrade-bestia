import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class FractalAggressiveV12(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    
    # RANGOS DE ESTUDIO (Hyperopt va a jugar con estos valores)
    buy_rsi = IntParameter(10, 60, default=30, space='buy')
    buy_mfi = IntParameter(10, 60, default=30, space='buy')
    buy_adx = IntParameter(15, 45, default=25, space='buy')
    buy_obv_factor = DecimalParameter(0.5, 2.0, default=1.0, space='buy')
    
    stoploss = -0.06
    minimal_roi = { "0": 0.10, "60": 0.05, "120": 0.02 }

    def informative_pairs(self):
        # Avisamos a Freqtrade que necesitamos datos de BTC
        return [("BTC/USDT", "5m")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # --- EL ARSENAL COMPLETO (DATOS PUROS) ---
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['mfi'] = ta.MFI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['obv'] = ta.OBV(dataframe)
        # OBV EMA para ver si el flujo sube o baja
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['volume_mean'] = ta.SMA(dataframe['volume'], timeperiod=30)
        
        # --- SENSOR BTC (CORREGIDO: Se ejecuta SIEMPRE) ---
        if self.dp:
            btc_df = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe="5m")
            # Calculamos indicador sobre BTC
            btc_df['ema_200_btc'] = ta.EMA(btc_df, timeperiod=200)
            
            # Merging con sufijos para no pisar datos
            # IMPORTANTE: Esto ahora corre en Hyperopt también
            dataframe = pd.merge(dataframe, btc_df[['date', 'ema_200_btc', 'close']], on='date', how='left', suffixes=('', '_btc'))
            
            # Rellenamos huecos por si acaso
            dataframe[['ema_200_btc', 'close_btc']] = dataframe[['ema_200_btc', 'close_btc']].ffill()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Chequeo de seguridad por si el merge falló (evita crash)
        if 'close_btc' in dataframe.columns:
            conditions = (
                (dataframe['close_btc'] > dataframe['ema_200_btc']) &  # BTC Sano
                (dataframe['close'] > dataframe['ema_200']) &         # Tendencia local
                (dataframe['rsi'] < self.buy_rsi.value) &             # RSI (Estudiado)
                (dataframe['mfi'] < self.buy_mfi.value) &             # MFI (Estudiado)
                (dataframe['adx'] > self.buy_adx.value) &             # Fuerza (Estudiado)
                # OBV Puro: Dinero inteligente entrando
                (dataframe['obv'] > dataframe['obv_ema'] * self.buy_obv_factor.value)
            )
            dataframe.loc[conditions, 'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Salida simple por ahora, dejamos que Hyperopt se concentre en la entrada
        dataframe.loc[(dataframe['rsi'] > 80), 'exit_long'] = 1
        return dataframe
