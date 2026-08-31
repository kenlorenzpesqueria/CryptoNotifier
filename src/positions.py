from datetime import datetime, timezone

from google.cloud import firestore


# Firestore client
db = firestore.Client()

POSITIONS_COLLECTION = "positions"


def load_positions():
    """
    Load all active positions from Firestore.

    Returns:
        dict: {
            "BTCUSDT": {
                "side": "BUY",
                "entry_price": 80457.60,
                "signal_time": "...",
                "status": "HEALTHY"
            }
        }
    """

    positions = {}

    docs = db.collection(POSITIONS_COLLECTION).stream()

    for doc in docs:
        positions[doc.id] = doc.to_dict()

    return positions


def save_positions(positions):
    """
    Save all positions to Firestore.

    Existing positions are updated.
    """

    collection = db.collection(POSITIONS_COLLECTION)

    for symbol, position in positions.items():
        collection.document(symbol).set(position)


def get_position(symbol):
    """
    Get one position from Firestore.
    """

    doc = (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
        .get()
    )

    if not doc.exists:
        return None

    return doc.to_dict()


def update_position(symbol, signal, price):
    """
    Create or replace a position.
    """

    position = {
        "side": signal,
        "entry_price": price,
        "signal_time": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        ),
        "status": "HEALTHY"
    }

    (
        db.collection(POSITIONS_COLLECTION)
        .document(symbol)
        .set(position)
    )


def close_position(symbol):
    """
    Remove an active position.
    """

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
    """
    Determine whether a new BUY/SELL signal should be sent.

    If there is no existing position:
        True

    If the existing position is the opposite side:
        True

    If the existing position has the same side:
        False
    """

    position = get_position(symbol)

    if position is None:
        return True

    return position.get("side") != signal


def update_status(symbol, status):
    """
    Update the status of an existing position.
    """

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
    """
    Evaluate whether an existing position is healthy
    or weakening based on current market conditions.
    """

    position = get_position(symbol)

    if position is None:
        return None

    old_status = position.get("status", "HEALTHY")

    if side == "BUY":
        weakening = (
            current["close"] < current["ema20"]
            or current["macd"] < 0
        )

    elif side == "SELL":
        weakening = (
            current["close"] > current["ema20"]
            or current["macd"] > 0
        )

    else:
        return None

    new_status = (
        "WEAKENING"
        if weakening
        else "HEALTHY"
    )

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