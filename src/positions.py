from datetime import datetime, timezone

from google.cloud import firestore


db = firestore.Client(project="cryptonotifier-503415")
POSITIONS_COLLECTION = "positions"


def load_positions():
    positions = {}

    docs = db.collection(POSITIONS_COLLECTION).stream()

    for doc in docs:
        positions[doc.id] = doc.to_dict()

    return positions


def get_position(symbol):
    doc = (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
        .get()
    )

    if not doc.exists:
        return None

    return doc.to_dict()


def update_position(symbol, signal, price):
    position = {
        "side": signal,
        "entry_price": price,
        "signal_time": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        ),
        "status": "HEALTHY",
    }

    (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
        .set(position)
    )


def close_position(symbol):
    doc_ref = (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
    )

    doc = doc_ref.get()

    if not doc.exists:
        return False

    doc_ref.delete()

    return True


def should_send(symbol, signal):
    position = get_position(symbol)

    if position is None:
        return True

    return position.get("side") != signal


def update_status(symbol, status):
    doc_ref = (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
    )

    doc = doc_ref.get()

    if not doc.exists:
        return False

    doc_ref.update({
        "status": status
    })

    return True


def evaluate_position(symbol, side, current):
    position = get_position(symbol)

    if position is None:
        return None

    old_status = position.get("status", "HEALTHY")

    if side == "BUY":
        weakening = (
            current["close"] < current["ema20"]
            or current["macd_hist"] < 0
        )

    elif side == "SELL":
        weakening = (
            current["close"] > current["ema20"]
            or current["macd_hist"] > 0
        )

    else:
        return None

    new_status = "WEAKENING" if weakening else "HEALTHY"

    if old_status != new_status:
        (
            db.collection(POSITIONS_COLLECTION)
            .document(symbol)
            .update({
                "status": new_status
            })
        )

        return new_status

    return None