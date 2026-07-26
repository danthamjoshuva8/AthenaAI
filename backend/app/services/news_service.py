from datetime import timedelta

import yfinance as yf


class NewsService:

    def get_historical_news(
        self,
        symbol: str,
        entry_date
    ):

        try:

            ticker = yf.Ticker(symbol)

            news = ticker.news or []

            results = []

            for item in news:

                publish_time = item.get("providerPublishTime")

                if publish_time is None:
                    continue

                publish_date = (
                    datetime.fromtimestamp(publish_time)
                )

                if publish_date.date() <= entry_date:

                    results.append({

                        "title": item.get("title"),

                        "publisher": item.get("publisher"),

                        "date": publish_date.strftime(
                            "%Y-%m-%d"
                        ),

                        "link": item.get("link")

                    })

            return results[:5]

        except Exception:

            return []