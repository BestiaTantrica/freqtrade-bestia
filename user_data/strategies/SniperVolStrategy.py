from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SniperVolStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # ROI: Escalonado para asegurar ganancias (Scalping agresivo)
    minimal_roi = {
        "0": 0.10,      # 10% instantáneo
        "20": 0.04,     # 4% en 20 mins
        "40": 0.015,    # 1.5% en 40 mins
        "120": 0.005    # 0.5% para salvar comisiones
    }
    
    stoploss = -0.06    # 6% Espacio para respirar
    
    # Trailing Stop: Protege ganancias
    trailing_stop = True
    trailing_stop_positive = 0.01       # Activa al 1%
    trailing_stop_positive_offset = 0.02 # Mantiene distancia del 2%
    trailing_only_offset_is_reached = True
    
    process_only_new_candles = True
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['lower'] = bollinger['lowerband']
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Volumen: Exigimos 2.0x el promedio
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['vol_spike'] = dataframe['volume'] > (dataframe['volume_mean'] * 2.0)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                # RESTAURADO: El precio debe estar 1% POR DEBAJO de la banda (El Escudo)
                (dataframe['close'] < (dataframe['lower'] * 0.99)) & 
                (dataframe['vol_spike'] == True)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe