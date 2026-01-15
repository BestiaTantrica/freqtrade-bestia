import requests, json, time, os

CONFIG_PATH = '/home/ec2-user/freqtrade-bestia/user_data/config_live.json'
URL = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT"

def obtener_cambio_real():
    try:
        r = requests.get(URL, timeout=10)
        return float(r.json()['priceChangePercent']) if r.status_code == 200 else 0.0
    except: return 0.0

def calcular_parametros(cambio):
    # 1. MODALIDAD EXTREMA: APOCALIPSIS
    if cambio < -5.0:
        return 15, -0.15  # RSI bajísimo (solo rebotes extremos) y SL largo
        
    # 2. MODALIDAD EXTREMA: EUFORIA (MOON)
    if cambio > 5.0:
        return 60, -0.05  # RSI alto (perseguir tendencia) y SL corto
    
    # 3. ZONA DINÁMICA (Estructura estándar)
    rsi_dinamico = int(35 + (cambio * 3))
    rsi_dinamico = max(20, min(55, rsi_dinamico))
    sl_dinamico = -0.05 if cambio > 0 else -0.10
    
    return rsi_dinamico, sl_dinamico

def mutar_cerebro():
    cambio = obtener_cambio_real()
    rsi, sl = calcular_parametros(cambio)
    
    try:
        with open(CONFIG_PATH, 'r') as f: config = json.load(f)
        actual_rsi = config['strategy_params'].get('buy_rsi', 0)
        
        if abs(actual_rsi - rsi) < 1: return # Evitar reinicios innecesarios

        config['stoploss'] = sl
        config['strategy_params'] = {"buy_rsi": rsi, "buy_adx": 20}
        
        with open(CONFIG_PATH, 'w') as f: json.dump(config, f, indent=4)
        print(f"🧠 CEREBRO V9: BTC {cambio}% -> Modo: {'Extremo' if abs(cambio)>5 else 'Dinámico'} | RSI: {rsi} | SL: {sl}")
        os.system("docker-compose restart freqtrade")
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        mutar_cerebro()
        time.sleep(300)
