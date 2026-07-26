import asyncio
import traceback

print("File Loaded")

from app.ai.orchestrator import AIOrchestrator

print("Import Successful")


async def main():
    try:
        print("Creating orchestrator")
        orchestrator = AIOrchestrator()

        print("Calling LLM...")
        result = await orchestrator.analyze_trade(
            trade = {
                "symbol": "RELIANCE",

                "entry": 1520,

                "stop_loss": 1480,

                "target": 1640,

                "score": 91,

                "strategy": "ATH Breakout",

                "risk_reward": "1:3",

                "breakout_type": "All Time High",

                "volume_strength": "Very High",
            },

            market={
                "trend": "Bullish",
                "nifty": 28700,
                "volatility": "Low",
                "market_strength": "Strong",
            },

            news={
                "sentiment": "Positive",
                "summary": "Strong quarterly earnings.",
            },

            portfolio={
                "cash": 500000,
                "positions": ["TCS", "INFY"],
                "open_trades": 2,
                "daily_risk": 0.6,
                "sector_exposure": {
                    "IT": 20,
                    "Energy": 5,
                },
            },

            history={
                "win_rate": 71,
                "avg_profit": 11.4,
                "avg_loss": -3.8,
                "last_trade": "Winner",
            },
        )

        print(result.model_dump())

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())