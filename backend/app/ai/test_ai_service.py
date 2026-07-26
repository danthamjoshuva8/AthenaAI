import asyncio

from app.ai.services.ai_trade_service import AITradeService


trade = {

    "symbol": "RELIANCE",

    "strategy": "ATH Breakout",

    "score": 92,

    "entry": 3025,

    "stop_loss": 2960,

    "target": 3220,

    "risk_reward": 3.0,

    "volume_strength": "High",

    "breakout_type": "Fresh ATH"

}


async def main():

    service = AITradeService()

    result = await service.evaluate_trade(trade)

    print()

    print("=" * 60)

    print(result.model_dump_json(indent=4))

    print("=" * 60)


asyncio.run(main())