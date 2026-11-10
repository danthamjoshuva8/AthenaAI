from app.forward_testing.portfolio_manager import ForwardTestingPortfolioManager


def candidate(symbol="RELIANCE", entry=100.0, stop=95.0):
    return {"symbol": symbol, "entry_price": entry, "stop_loss": stop}


def test_position_size_respects_risk_and_allocation():
    manager = ForwardTestingPortfolioManager()
    result = manager.calculate_position_size(
        entry_price=100,
        stop_loss=95,
        available_capital=100_000,
        remaining_portfolio_risk=5_000,
    )
    assert result["eligible"] is True
    assert result["quantity"] == 200
    assert result["position_value"] == 20_000
    assert result["risk_amount"] == 1_000


def test_rejects_invalid_stop_loss():
    manager = ForwardTestingPortfolioManager()
    result = manager.calculate_position_size(
        entry_price=100,
        stop_loss=100,
        available_capital=50_000,
        remaining_portfolio_risk=5_000,
    )
    assert result["eligible"] is False


def test_duplicate_symbol_is_rejected():
    manager = ForwardTestingPortfolioManager()
    result = manager.evaluate_candidates(
        candidates=[candidate(), candidate()],
        available_capital=100_000,
    )
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 1
    assert "duplicated" in result["rejected"][0]["reason"]


def test_existing_position_blocks_same_symbol():
    manager = ForwardTestingPortfolioManager()
    result = manager.evaluate_candidates(
        candidates=[candidate()],
        current_positions=[{
            "symbol": "RELIANCE", "quantity": 10,
            "entry_price": 100, "stop_loss": 95,
        }],
        available_capital=90_000,
    )
    assert result["accepted_count"] == 0
    assert "already exists" in result["rejected"][0]["reason"]


def test_daily_entry_limit_is_applied():
    manager = ForwardTestingPortfolioManager()
    result = manager.evaluate_candidates(
        candidates=[candidate("A"), candidate("B")],
        available_capital=100_000,
        entries_today=2,
    )
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 1
    assert "Daily new-position limit" in result["rejected"][0]["reason"]


def test_max_open_positions_is_applied():
    manager = ForwardTestingPortfolioManager()
    positions = [
        {"symbol": f"OLD{i}", "quantity": 1, "entry_price": 100, "stop_loss": 95}
        for i in range(5)
    ]
    result = manager.evaluate_candidates(
        candidates=[candidate("NEW")],
        current_positions=positions,
        available_capital=100_000,
    )
    assert result["accepted_count"] == 0
    assert "Maximum open positions" in result["rejected"][0]["reason"]
