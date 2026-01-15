from freqtrade.strategy import IStrategy, IntParameter
import pandas as pd
import pandas_ta as ta

class GuruStrategy(IStrategy):
    force_entry_enable = True
    INTERFACE_VERSION = 3
    timeframe = '5m'
    
    # Parámetro optimizado por Hyperopt
    buy_rsi = IntParameter(5, 30, default=10, space='buy')

    # Nueva tabla ROI optimizada por la IA (Epoch 83)
    minimal_roi = {
        "0": 0.199,
        "17": 0.027,
        "75": 0.017,
        "187": 0
    }
    
    # Regla de Oro de Tomás (Blindaje de capital)
    stoploss = -0.05 

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe['rsi'] < self.buy_rsi.value), 
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Salida gestionada puramente por la tabla ROI y Stoploss
        dataframe.loc[(dataframe['rsi'] > 99), 'exit_long'] = 1 
        return dataframe