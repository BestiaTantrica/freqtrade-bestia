from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter, Trade
from pandas import DataFrame
from datetime import datetime
import talib.abstract as ta


class SniperV5_MathLab(IStrategy):
    INTERFACE_VERSION = 3

    # --- CONFIGURACIÓN MAESTRA V8 (Pure ROI) ---
    # Foco: Si entramos, confiamos. No salimos por sustos técnicos (RSI).
    # Solo salimos con Dinero en el bolsillo (ROI) o para salvar el barco (Stoploss).

    # 1. ROI Táctico (Ajustado para asegurar profit medio)
    minimal_roi = {
        "0": 0.30,  # 30% instantáneo (Pump)
        "60": 0.08,  # 8% a la hora (Bajamos la vara para asegurar)
        "120": 0.04,  # 4% a las 2 horas
        "240": 0.02,  # 2% a las 4 horas
        "720": 0.015,  # 1.5% a las 12 horas (Mínimo aceptable)
        "1440": 0,  # A las 24 horas, break-even
    }

    # 2. Stoploss y Trailing (Blindaje Spot)
    stoploss = -0.25

    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.08
    trailing_only_offset_is_reached = True

    # --- PARÁMETROS DE COMPRA (Sniper V7 Hardening Mantenido) ---
    buy_rvol_threshold = DecimalParameter(1.5, 3.5, default=2.2, space="buy", load=True)
    atr_period = IntParameter(10, 40, default=20, space="buy", load=True)
    buy_rsi = IntParameter(20, 45, default=30, space="buy", load=True)
    buy_adx = IntParameter(20, 50, default=25, space="buy", load=True)

    timeframe = "5m"
    process_only_new_candles = True
    startup_candle_count: int = 500

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Indicadores Base
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # --- VOLUMEN RELATIVO (RVOL) ---
        dataframe["volume_usd_candle"] = dataframe["volume"] * dataframe["close"]
        dataframe["volume_mean_24h"] = dataframe["volume_usd_candle"].rolling(window=288).mean()
        dataframe["rvol"] = dataframe["volume_usd_candle"] / dataframe["volume_mean_24h"]

        # --- VOLATILIDAD (ATR) ---
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        dataframe["atr_mean_24h"] = dataframe["atr"].rolling(window=288).mean()
        dataframe["volatility_ratio"] = dataframe["atr"] / dataframe["atr_mean_24h"]

        # --- DETECTOR DE CONTEXTO TENDENCIAL ---
        dataframe["ema_dist"] = (dataframe["close"] - dataframe["ema200"]) / dataframe["ema200"]

        # Volumen acumulado 24h
        dataframe["volume_usd_24h"] = dataframe["volume_usd_candle"].rolling(window=288).sum()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rvol"] > self.buy_rvol_threshold.value)
                & (dataframe["rsi"] < self.buy_rsi.value)
                & (dataframe["adx"] > 20)
                & (dataframe["close"] > dataframe["ema200"])
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # --- V8 CHANGE: SIN SALIDA TÉCNICA ---
        # Confiamos ciegamente en ROI y STOPLOSS.
        # Si la moneda sube a RSI 80, ¡mejor! Dejamos que el ROI la capture.
        # No cortamos las ganancias (ni aceptamos pérdidas parciales en rebotes).
        return dataframe

    # --- LÓGICA DE STAKE DINÁMICO (V7 INSTITUTIONAL MANTENIDO) ---
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        **kwargs,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return proposed_stake

        last_row = dataframe.iloc[-1]
        last_vol_24h = last_row["volume_usd_24h"]
        vol_ratio = last_row["volatility_ratio"]
        ema_dist = last_row["ema_dist"]

        # --- 1. GUARDIA ELÁSTICA ---
        is_safe_bull = ema_dist > 0.04

        if vol_ratio > 1.9 and not is_safe_bull:
            return proposed_stake * 0.30

        # --- 2. TURBO-BULL ---
        if is_safe_bull:
            return proposed_stake * 1.0

        # --- 3. FILTRO DE SEGURIDAD ---
        if last_vol_24h > 1000000000:
            return proposed_stake
        elif last_vol_24h > 300000000:
            return proposed_stake * 0.70
        else:
            return 0.0

    # --- SALIDA ELÁSTICA (SIN TIME-OUT) ---
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        return None
