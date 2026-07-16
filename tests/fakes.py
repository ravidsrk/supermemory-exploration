from typing import Any, Dict, List, Mapping, Optional, Tuple


class RecordingTransport:
    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None) -> None:
        self.calls: List[Tuple[str, str, Optional[Mapping[str, Any]]]] = []
        self.responses = list(responses or [])

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.calls.append((method, path, body))
        return self.responses.pop(0) if self.responses else {"ok": True}
