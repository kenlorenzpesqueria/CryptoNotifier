from datetime import datetime, timezone

from google.cloud import firestore


db = firestore.Client(project="cryptonotifier-503415")

POSITIONS_COLLECTION = "positions"
SIGNAL_TRACKING_COLLECTION = "signal_tracking"


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
        "ema20_alerted": False,
    }

    (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
        .set(position)
    )

    clear_signal_tracking(symbol)


def close_position(symbol):
    doc_ref = (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
    )

    doc = doc_ref.get()

    if not doc.exists:
        return False

    doc_ref.delete()
    clear_signal_tracking(symbol)

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


def check_ema20_breach(symbol, side, current_4h):
    position = get_position(symbol)

    if position is None:
        return False

    if side != "BUY":
        return False

    close_price = float(current_4h["close"])
    ema20 = float(current_4h["ema20"])

    below_ema20 = close_price < ema20
    already_alerted = position.get(
        "ema20_alerted",
        False,
    )

    if below_ema20:
        if already_alerted:
            return False

        (
            db.collection(POSITIONS_COLLECTION)
            .document(symbol)
            .update({
                "status": "WEAKENING",
                "ema20_alerted": True,
            })
        )

        return True

    if already_alerted:
        (
            db.collection(POSITIONS_COLLECTION)
            .document(symbol)
            .update({
                "status": "HEALTHY",
                "ema20_alerted": False,
            })
        )

    return False


def get_signal_tracking(symbol):
    doc = (
        db.collection(SIGNAL_TRACKING_COLLECTION)
        .document(symbol)
        .get()
    )

    if not doc.exists:
        return None

    return doc.to_dict()


def save_signal_tracking(
    symbol,
    signal,
    close_price,
    macd,
    signal_time=None,
):
    if signal_time is None:
        signal_time = datetime.now(timezone.utc)

    if hasattr(signal_time, "to_pydatetime"):
        signal_time = signal_time.to_pydatetime()

    if signal_time.tzinfo is None:
        signal_time = signal_time.replace(
            tzinfo=timezone.utc
        )
    else:
        signal_time = signal_time.astimezone(
            timezone.utc
        )

    tracking = {
        "side": signal,
        "signal_close": float(close_price),
        "signal_macd": float(macd),
        "signal_time": signal_time.strftime(
            "%Y-%m-%d %H:%M"
        ),
    }

    (
        db.collection(SIGNAL_TRACKING_COLLECTION)
        .document(symbol)
        .set(tracking)
    )


def clear_signal_tracking(symbol):
    (
        db.collection(SIGNAL_TRACKING_COLLECTION)
        .document(symbol)
        .delete()
    )