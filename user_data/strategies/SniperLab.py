from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
from pandas import DataFrame

class SniperLab(IStrategy):
    force_entry_enable = True
    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = True
    startup_candle_count = 100

    minimal_roi = {"0": 0.098, "19": 0.064, "75": 0.013, "192": 0}
    stoploss = -0.338
    trailing_stop = True
    trailing_stop_positive = 0.218
    trailing_stop_positive_offset = 0.251
    trailing_only_offset_is_reached = True

    buy_rsi = IntParameter(10, 40, default=22, space="buy")
    buy_adx = IntParameter(5, 50, default=20, space="buy")
    sell_rsi = IntParameter(60, 95, default=72, space="sell")
    sell_adx = IntParameter(5, 50, default=5, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['resistencia_macro'] = dataframe['high'].rolling(window=500).max()
        dataframe['soporte_macro'] = dataframe['low'].rolling(window=500).min()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[((dataframe['rsi'] < self.buy_rsi.value) & (dataframe['adx'] > self.buy_adx.value)), ['enter_long', 'enter_tag']] = (1, 'long_sniper')
        dataframe.loc[((dataframe['rsi'] > self.sell_rsi.value) & (dataframe['adx'] > self.sell_adx.value)), ['enter_short', 'enter_tag']] = (1, 'short_sniper')
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[((dataframe['rsi'] > self.sell_rsi.value)), 'exit_long'] = 1
        dataframe.loc[((dataframe['rsi'] < self.buy_rsi.value)), 'exit_short'] = 1
        return dataframe