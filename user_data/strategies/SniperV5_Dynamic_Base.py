from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SniperV5_MathLab(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    process_only_new_candles = True
    startup_candle_count: int = 500
    
    minimal_roi = {"0": 0.30, "60": 0.08, "240": 0.02, "1440": 0}
    stoploss = -0.25
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.08
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Usamos self.config para leer DIRECTAMENTE del cerebro (JSON)
        # Si no existe en el JSON, usa 30 y 25 por defecto.
        rsi_threshold = self.config.get('strategy_params', {}).get('buy_rsi', 30)
        adx_threshold = self.config.get('strategy_params', {}).get('buy_adx', 25)
        
        dataframe.loc[
            (
                (dataframe["rsi"] < rsi_threshold) &
                (dataframe["adx"] > adx_threshold)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
