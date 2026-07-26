from app.ai.models.news_analysis import NewsAnalysis


class NewsService:

    """
    Placeholder News Service.

    Future providers:
    - NewsAPI
    - Finnhub
    - Alpha Vantage
    - Polygon
    - MoneyControl
    """

    async def analyze(
        self,
        symbol: str
    ) -> NewsAnalysis:

        return NewsAnalysis(
            symbol=symbol,
            news_score=50,
            sentiment_score=50,
            confidence=50,
            summary="News integration pending."
        )