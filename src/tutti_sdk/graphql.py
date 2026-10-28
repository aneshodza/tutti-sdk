from typing import Any

from .errors import TuttiGraphQLError
from .http import HttpClient
from .operations import Operation


class GraphQLTransport:
    """Runs GraphQL operations over an HttpClient. Operation-agnostic: add a new
    operation to ``operations.py`` and call ``request`` — no change here."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def request(self, op: Operation, variables: dict[str, Any]) -> Any:
        """Execute an operation and return its unwrapped root field (``data[root_field]``)."""
        json = self._http.request(
            "POST",
            "/graphql",
            body={"operationName": op.name, "query": op.document, "variables": variables},
            headers={
                "X-APOLLO-OPERATION-NAME": op.name,
                "X-APOLLO-OPERATION-ID": op.id,
                "Accept": "multipart/mixed; deferSpec=20220824, application/json",
            },
        )
        if json.get("errors"):
            raise TuttiGraphQLError(op.name, json["errors"])
        data = json.get("data")
        if data is None:
            raise TuttiGraphQLError(op.name, [{"message": "response contained no data"}])
        return data.get(op.root_field)
