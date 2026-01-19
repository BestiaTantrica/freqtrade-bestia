import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, merge_informative_pair
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import json
import os

class FractalMasterSelector(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    inf_timeframe = '1h'
    stoploss = -0.10
    minimal_roi = {"0": 100}

    # Parámetros Originales
    buy_params = {
        "v18_adx": 30, "v18_rsi": 60,
        "v17_rsi": 25,
        "v15_adx": 25, "v15_rsi": 45
    }

    def informative_pairs(self):
        return [("BTC/USDT", self.inf_timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Indicadores base
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['bb_lower'] = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2.5)['lower']
        
        # Juez BTC 1h
        inf_tf = self.dp.get_pair_dataframe("BTC/USDT", self.inf_timeframe)
        inf_tf['ema_200'] = ta.EMA(inf_tf, timeperiod=200)
        dataframe = merge_informative_pair(dataframe, inf_tf, self.timeframe, self.inf_timeframe, ffill=True)
        
        # Filtros técnicos de soporte
        dataframe['es_bull'] = (dataframe[f'close_{self.inf_timeframe}'] > dataframe[f'ema_200_{self.inf_timeframe}'])
        dataframe['es_bear'] = (dataframe[f'close_{self.inf_timeframe}'] < dataframe[f'ema_200_{self.inf_timeframe}'])
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # --- LECTURA DEL SENTINELA ---
        path_estado = os.path.join('user_data', 'market_state.json')
        try:
            with open(path_estado, 'r') as f:
                sentinel = json.load(f)
                score = sentinel['sentiment_score']
                modo = sentinel['active_mode']
        except:
            score = 0
            modo = "v15_camaleon"

        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_tag'] = ''

        # 1. MODO ESPADA (Sentimiento 2, 3, 4)
        if modo == "v18_espada":
            # Si hay euforia (+4), bajamos exigencia de ADX para entrar rápido
            adx_min = 25 if score == 4 else 30
            mask = (dataframe['es_bull'] & (dataframe['adx'] > adx_min) & (dataframe['rsi'] > 60))
            dataframe.loc[mask, ['enter_long', 'enter_tag']] = [1, 'v18_espada']

        # 2. MODO ESCUDO (Sentimiento -2, -3, -4)
        elif modo == "v17_escudo":
            # Si hay pánico (-4), pedimos RSI más bajo aún
            rsi_max = 18 if score == -4 else 25
            mask = (dataframe['es_bear'] & (dataframe['rsi'] < rsi_max) & (dataframe['close'] < dataframe['bb_lower']))
            dataframe.loc[mask, ['enter_long', 'enter_tag']] = [1, 'v17_escudo']

        # 3. MODO CAMALEON (Sentimiento -1, 0, 1)
        elif modo == "v15_camaleon":
            mask = (~dataframe['es_bull'] & ~dataframe['es_bear'] & (dataframe['adx'] < 25))
            dataframe.loc[mask, ['enter_long', 'enter_tag']] = [1, 'v15_camaleon']

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe