import json
from datetime import datetime

POSITION_FILE="data/positions.json"

def load_positions():
    try:
        with open(POSITION_FILE,"r") as f:
            return json.load(f)
    except:
        return {}

def save_positions(positions):
    with open(POSITION_FILE,"w") as f:
        json.dump(positions,f,indent=4)

def get_position(symbol):
    positions=load_positions()
    return positions.get(symbol)

def update_position(symbol,signal,price):
    positions=load_positions()
    positions[symbol]={
        "side":signal,
        "entry_price":price,
        "signal_time":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status":"HEALTHY"
    }
    save_positions(positions)

def should_send(symbol,signal):
    positions=load_positions()
    if symbol not in positions:
        return True
    return positions[symbol]["side"]!=signal

def update_status(symbol,status):
    positions=load_positions()
    if symbol not in positions:
        return False
    positions[symbol]["status"]=status
    save_positions(positions)
    return True

def evaluate_position(symbol,side,current):
    positions=load_positions()
    if symbol not in positions:
        return None

    position=positions[symbol]
    old_status=position.get("status","HEALTHY")

    if side=="BUY":
        weakening=(
            current["close"]<current["ema20"]
            or current["macd"]<current["macd_signal"]
        )
    elif side=="SELL":
        weakening=(
            current["close"]>current["ema20"]
            or current["macd"]>current["macd_signal"]
        )
    else:
        return None

    new_status="WEAKENING" if weakening else "HEALTHY"

    if old_status!=new_status:
        position["status"]=new_status
        save_positions(positions)
        return new_status

    return None