from datetime import datetime

import yfinance as yf


class NewsProvider:
    """
    Retrieves historical news articles for a given stock symbol.

    Uses Yahoo Finance news data and filters articles based on
    their publication date relative to the trade entry date.
    """

    def get_historical_news(
        self,
        symbol: str,
        entry_date
    ):
        """
        Retrieve news articles published on or before the entry date.

        Args:
            symbol: Stock ticker symbol used to retrieve Yahoo Finance news.
            entry_date: Trade entry date used to filter published articles.

        Returns:
            A list containing up to five news articles. Each article
            includes its title, publisher, publication date, and link.
            Returns an empty list if retrieval or processing fails.
        """

        try:
            # Initialize the Yahoo Finance ticker for the requested symbol.
            ticker = yf.Ticker(symbol)

            # Retrieve available news articles.
            news = ticker.news or []

            results = []

            # Process each article and check its publication date.
            for item in news:

                # Retrieve the article's publication timestamp.
                publish_time = item.get("providerPublishTime")

                # Skip articles without a publication timestamp.
                if publish_time is None:
                    continue

                # Convert the Unix timestamp into a datetime object.
                publish_date = (
                    datetime.fromtimestamp(publish_time)
                )

                # Include only articles published on or before the entry date.
                if publish_date.date() <= entry_date:

                    results.append({

                        "title": item.get("title"),

                        "publisher": item.get("publisher"),

                        "date": publish_date.strftime(
                            "%Y-%m-%d"
                        ),

                        "link": item.get("link")

                    })

            # Return at most the five most recently encountered matching articles.
            return results[:5]

        except Exception:
            # Return an empty list if news retrieval or processing fails.
            return []