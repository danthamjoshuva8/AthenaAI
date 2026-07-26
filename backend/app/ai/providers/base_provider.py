from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    async def analyze_trade(self, prompt: str):

        pass