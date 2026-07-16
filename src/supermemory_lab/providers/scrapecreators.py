"""ScrapeCreators public social-signal adapter."""

from typing import Optional

from ..http import JsonObject, JsonTransport
from .query import with_query


class ScrapeCreatorsClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def credit_balance(self) -> JsonObject:
        return self._transport.request("GET", "/v1/account/credit-balance")

    def twitter_profile(self, handle: str) -> JsonObject:
        return self._transport.request(
            "GET", with_query("/v1/twitter/profile", {"handle": handle})
        )

    def twitter_tweets(self, handle: str, *, trim: bool = True) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query("/v1/twitter/user-tweets", {"handle": handle, "trim": trim}),
        )

    def reddit_search(
        self,
        query: str,
        *,
        sort: str = "relevance",
        timeframe: str = "month",
        after: Optional[str] = None,
        trim: bool = True,
    ) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                "/v1/reddit/search",
                {
                    "query": query,
                    "sort": sort,
                    "timeframe": timeframe,
                    "after": after,
                    "trim": trim,
                },
            ),
        )

    def github_trending(
        self, *, language: Optional[str] = None, since: str = "weekly"
    ) -> JsonObject:
        return self._transport.request(
            "GET",
            with_query(
                "/v1/github/trending/repositories",
                {"language": language, "since": since},
            ),
        )
