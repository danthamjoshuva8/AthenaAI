def sort_ai_trades(trades: list):

    priority = {
        "BUY": 3,
        "HOLD": 2,
        "REJECT": 1
    }

    return sorted(
        trades,
        key=lambda x: (
            priority.get(x["ai_decision"], 0),
            x["ai_confidence"],
            x["score"]
        ),
        reverse=True
    )