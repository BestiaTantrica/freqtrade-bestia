# --- ESTRATEGIA SNIPER V4 - HYPEROPT READY ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class SniperVolStrategy(IStrategy):
    force_entry_enable = True
    INTERFACE_VERSION = 3
    
    # Tiempos y ROI (Serán sobreescritos por Hyperopt)
    timeframe = '5m'
    minimal_roi = {"0": 0.05}
    stoploss = -0.10
    
    # --- PERILLAS DE OPTIMIZACIÓN (AQUÍ OCURRE LA MAGIA) ---
    buy_rsi = IntParameter(15, 35, default=30, space="buy")
    buy_adx = IntParameter(15, 40, default=25, space="buy")
    sell_rsi = IntParameter(65, 85, default=70, space="sell")
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Indicadores Básicos
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe)
        
        # Bandas de Bollinger (Para volatilidad)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        
        # --- CONCIENCIA MACRO (Techos y Pisos Históricos) ---
        # Usamos ventanas grandes para simular historia reciente
        dataframe['resistencia_macro'] = dataframe['high'].rolling(window=500).max()
        dataframe['soporte_macro'] = dataframe['low'].rolling(window=500).min()
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # CONDICIÓN 1: RSI en zona de sobreventa (OPTIMIZABLE)
                (dataframe['rsi'] < self.buy_rsi.value) &
                # CONDICIÓN 2: Tendencia definida (ADX)
                (dataframe['adx'] > self.buy_adx.value) &
                # CONDICIÓN 3: Precio cerca del piso de las bandas (Rebote)
                (dataframe['close'] < dataframe['bb_lowerband']) &
                # CONDICIÓN 4: Volumen presente (filtro básico)
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Salida por RSI alto (OPTIMIZABLE)
                (dataframe['rsi'] > self.sell_rsi.value)
            ),
            'exit_long'] = 1
        return dataframe