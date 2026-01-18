import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class FractalBajistaV17B(IStrategy):
    """
    Estrategia FractalBajistaV17B - Edición Inmortal
    Sobreviviente de Mayo 2021, FTX 2022 e Invierno Cripto.
    """
    INTERFACE_VERSION = 3
    timeframe = '5m'

    # --- PARÁMETROS FIJADOS (RESULTADOS DEL HYPEROPT) ---
    # Los definimos como parámetros de clase para que Freqtrade los vea bien
    b1_rsi = IntParameter(10, 45, default=22, space='buy')
    b1_bb_offset = DecimalParameter(0.90, 1.10, default=0.978, space='buy')

    b2_rsi = IntParameter(5, 30, default=16, space='buy')
    b2_bb_offset = DecimalParameter(0.85, 1.05, default=0.944, space='buy')

    b3_rsi = IntParameter(1, 20, default=9, space='buy')
    b3_bb_offset = DecimalParameter(0.70, 0.95, default=0.862, space='buy')

    sell_rsi = IntParameter(40, 95, default=81, space='sell')

    # --- GESTIÓN DE RIESGO ---
    stoploss = -0.10
    minimal_roi = {
        "0": 0.10,      # Buscar 10% de rebote inmediato
        "30": 0.05,     # A los 30 min, aceptar 5%
        "60": 0.02,     # A la hora, asegurar 2%
        "120": 0        # A las 2 horas, salir si no hay pérdida
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI para medir el pánico
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Bandas de Bollinger para medir la desviación del precio
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lowerband'] = bollinger['lowerband']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Capa 1: Pánico Leve (La más activa)
        b1 = (dataframe['rsi'] < self.b1_rsi.value) & \
             (dataframe['close'] < dataframe['bb_lowerband'] * self.b1_bb_offset.value)
        
        # Capa 2: Pánico Normal (Capitulación)
        b2 = (dataframe['rsi'] < self.b2_rsi.value) & \
             (dataframe['close'] < dataframe['bb_lowerband'] * self.b2_bb_offset.value)
        
        # Capa 3: Pánico Extremo (Flash Crash / Mechas)
        b3 = (dataframe['rsi'] < self.b3_rsi.value) & \
             (dataframe['close'] < dataframe['bb_lowerband'] * self.b3_bb_offset.value)

        # Aplicamos las señales con sus etiquetas para el reporte
        dataframe.loc[b1, ['enter_long', 'enter_tag']] = (1, 'panico_LEVE_b1')
        dataframe.loc[b2, ['enter_long', 'enter_tag']] = (1, 'panico_NORMAL_b2')
        dataframe.loc[b3, ['enter_long', 'enter_tag']] = (1, 'panico_EXTREMO_b3')
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Salida cuando el RSI recupera fuerza (fin del rebote)
        dataframe.loc[
            (dataframe['rsi'] > self.sell_rsi.value),
            'exit_long'
        ] = 1
        return dataframe