from dataclasses import dataclass


@dataclass
class StrategyFeatures:

    trend_strength: float = 0.0

    volume_strength: float = 0.0

    breakout_strength: float = 0.0

    momentum_strength: float = 0.0

    risk_reward_strength: float = 0.0

    relative_strength: float = 0.0

    liquidity_strength: float = 0.0