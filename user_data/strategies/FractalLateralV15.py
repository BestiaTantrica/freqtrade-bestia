import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class FractalLateralV15(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'

    # --- PARÁMETROS FINALES OPTIMIZADOS (16 MESES DE ESTUDIO) ---
    
    # Capa de Clima: Si el ADX de BTC es mayor a 13, la Bestia Lateral se apaga.
    max_adx_lateral = IntParameter(10, 30, default=13, space='buy')
    
    # MODO 1: Cangrejo POCO (Squeeze de Bandas)
    # Este entra cuando el precio toca casi exactamente la banda inferior.
    c1_rsi_entry = IntParameter(25, 45, default=32, space='buy')
    c1_bb_offset = DecimalParameter(0.98, 1.02, default=0.999, space='buy')

    # MODO 2: Cangrejo NORMAL (El que preguntabas: El Corazón del Rango)
    # Este busca una sobreventa clara de RSI para rebotar al medio.
    c2_rsi_entry = IntParameter(20, 40, default=22, space='buy')
    c2_rsi_exit = IntParameter(60, 80, default=61, space='sell')

    # MODO 3: Cangrejo MUCHO (Cazador de Volatilidad en Rango)
    # Solo entra si hay "lío" (ATR alto), buscando el pánico de las mechas.
    c3_rsi_entry = IntParameter(15, 35, default=20, space='buy')
    c3_atr_threshold = DecimalParameter(0.5, 2.5, default=1.979, space='buy')

    # --- CONFIGURACIÓN DE GESTIÓN DE RIESGO ---
    stoploss = -0.05  # Si el rango se rompe fuerte, salimos con 5% de pérdida.
    
    minimal_roi = {
        "0": 0.05,      # Buscamos 5% rápido
        "30": 0.02,     # A la media hora nos conformamos con 2%
        "60": 0         # Si en una hora no pasó nada, salimos para liberar capital
    }

    max_open_trades = 3

    def informative_pairs(self):
        return [("BTC/USDT", "5m")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Indicadores para el par que estemos tradeando
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # Bandas de Bollinger para detectar techos y suelos
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lowerband'] = bollinger['lowerband']
        dataframe['bb_upperband'] = bollinger['upperband']

        # Datos de BTC para el "Cerebro" que detecta si el mercado está quieto
        if self.dp:
            btc_df = self.dp.get_pair_dataframe(pair="BTC/USDT", timeframe="5m")
            btc_df['adx_btc'] = ta.ADX(btc_df, timeperiod=14)
            dataframe = pd.merge(dataframe, btc_df[['date', 'adx_btc']], on='date', how='left')
            dataframe.ffill(inplace=True)
            
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Condición Maestra: Solo si BTC está en modo "Lateral" (ADX < 13)
        clima_lateral = (dataframe['adx_btc'] < self.max_adx_lateral.value)

        # MODO 1: POCO (Toque de banda inferior + RSI < 32)
        c1_entry = (
            clima_lateral & 
            (dataframe['rsi'] < self.c1_rsi_entry.value) &
            (dataframe['close'] < dataframe['bb_lowerband'] * self.c1_bb_offset.value)
        )

        # MODO 2: NORMAL (RSI < 22) - Entrada por agotamiento puro
        c2_entry = (
            clima_lateral & 
            (dataframe['rsi'] < self.c2_rsi_entry.value)
        )

        # MODO 3: MUCHO (RSI < 20 + ATR Muy Alto) - Entrada en mechas de pánico
        c3_entry = (
            clima_lateral &
            (dataframe['rsi'] < self.c3_rsi_entry.value) &
            (dataframe['atr'] > dataframe['atr'].rolling(20).mean() * self.c3_atr_threshold.value)
        )

        # Si cualquiera de los 3 modos se activa, la Bestia compra
        dataframe.loc[c1_entry | c2_entry | c3_entry, 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Salida: Cuando el RSI llega a 61 (según Hyperopt) o toca el techo del rango (BB Upper)
        dataframe.loc[
            (dataframe['rsi'] > self.c2_rsi_exit.value) | 
            (dataframe['close'] > dataframe['bb_upperband']), 
            'exit_long'
        ] = 1
        return dataframe