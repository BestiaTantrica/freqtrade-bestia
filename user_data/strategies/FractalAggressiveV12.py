from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class FractalAggressiveV12(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    
    # ROI: Aseguramos el 2% rápido
    minimal_roi = {"0": 0.02, "45": 0.01}
    
    # Stoploss: Protegemos los 300 USDT
    stoploss = -0.012

    # Trailing Stop: Si ganamos, aseguramos
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.011
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA 200: Nuestro filtro de seguridad (Modo Búnker vs Modo Ataque)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Bandas de Bollinger (Estándar 2.0 para buena frecuencia de trades)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2.0)
        dataframe['bb_lowerband'] = bollinger['lower']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # REGLA DE ORO: Solo compramos si el mercado es alcista (Precio > EMA 200)
                (dataframe['close'] > dataframe['ema_200']) & 
                # Compramos el retroceso (Precio toca banda inferior)
                (dataframe['close'] < dataframe['bb_lowerband']) &
                # RSI confirma que no está sobrecomprado
                (dataframe['rsi'] < 45)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Salida por RSI alto (fuerza de venta)
        dataframe.loc[(dataframe['rsi'] > 75), 'exit_long'] = 1
        return dataframe
