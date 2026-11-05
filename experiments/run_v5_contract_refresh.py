"""Live November 2026 v5 contract refresh (synthetic namespace, full cleanup).

Requires SUPERMEMORY_API_KEY in the process environment or ignored .env.local.
If the key is missing the script exits with a clear blocked message instead of failing.
"""

from datetime import datetime, timezone
import json
import os
import secrets
import sys

from supermemory_lab.http import UrlLibTransport
from supermemory_lab.redaction import redact
from supermemory_lab.trace import RunTrace
from supermemory_lab.v5_refresh import V5RefreshProbe


def main() -> int:
    try:
        from supermemory_lab.config import load_config

        config = load_config()
    except RuntimeError:
        print(json.dumps({"status": "blocked", "reason": "SUPERMEMORY_API_KEY not configured"}))
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)
    run_id = f"v5refresh-{stamp}-{suffix}"
    transport = UrlLibTransport(config.supermemory_base_url, config.supermemory_api_key, timeout_seconds=60)
    probe = V5RefreshProbe(
        transport,
        namespace=f"lab:v5refresh:{stamp}-{suffix}",
        canary=f"V5REFRESH_{suffix.upper()}",
        timeout_seconds=float(os.environ.get("V5_REFRESH_TIMEOUT", "180")),
    )
    trace = RunTrace(run_id, experiment="v5-contract-refresh-2026-11")
    report = probe.run()
    trace.metric("report", report)
    path = trace.write()
    print(json.dumps(redact({"trace": str(path), **report}), indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
