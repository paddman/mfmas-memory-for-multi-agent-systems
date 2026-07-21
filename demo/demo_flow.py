#!/usr/bin/env python3
"""End-to-end NT MemoryVault demo using only the Python standard library."""

from __future__ import annotations

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "http://localhost:8000"
TENANT = "nt-demo"
SUBJECT = "CUST-1001"


def headers(agent: str, role: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Tenant-ID": TENANT,
        "X-Agent-ID": agent,
        "X-Agent-Role": role,
    }


def call(path: str, method: str = "GET", body: dict | None = None, *, agent: str, role: str):
    payload = json.dumps(body).encode() if body is not None else None
    request = Request(API + path, data=payload, method=method, headers=headers(agent, role))
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def wait_for_api() -> None:
    for _ in range(30):
        try:
            with urlopen(API + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(1)
    raise RuntimeError("MemoryVault API is not ready")


def main() -> int:
    wait_for_api()
    print("\nNT MemoryVault — Customer Continuity Demo\n")

    call(
        f"/v1/subjects/{SUBJECT}/memories",
        method="DELETE",
        agent="demo-admin",
        role="admin",
    )

    shared = call(
        "/v1/memories",
        method="POST",
        agent="support-agent-qwen",
        role="support",
        body={
            "subject_id": SUBJECT,
            "scope": "customer-continuity",
            "type": "preference",
            "content": "ลูกค้ามี 3 สาขา ต้องการใบเสนอราคา และสะดวกให้ติดต่อหลัง 17:00",
            "source": "line-conversation-2026-07-21",
            "confidence": 0.97,
            "sensitivity": "internal",
            "allowed_roles": ["support", "sales"],
            "metadata": {"channel": "LINE", "consent": True},
        },
    )
    print(f"1. Support wrote shared memory: {shared['id']}")

    restricted = call(
        "/v1/memories",
        method="POST",
        agent="support-agent-qwen",
        role="support",
        body={
            "subject_id": SUBJECT,
            "scope": "support-private",
            "type": "event",
            "content": "ลูกค้าเคยร้องเรียนรุนแรงและขอให้หัวหน้าทีมเป็นผู้รับผิดชอบเท่านั้น",
            "source": "support-ticket-8842",
            "confidence": 0.93,
            "sensitivity": "restricted",
            "allowed_roles": ["support"],
            "metadata": {"channel": "ticket", "consent": False},
        },
    )
    print(f"2. Support wrote restricted memory: {restricted['id']}")

    result = call(
        "/v1/memories/search",
        method="POST",
        agent="sales-agent-claude",
        role="sales",
        body={
            "query": "สาขา ใบเสนอราคา ติดต่อ",
            "subject_id": SUBJECT,
            "limit": 10,
        },
    )
    print(f"3. Sales retrieved {len(result['results'])} memory record(s)")
    print(f"4. Policy denied {result['denied_count']} restricted record(s)")
    for item in result["results"]:
        print(f"   → {item['memory']['content']}")

    events = call(
        f"/v1/audit?subject_id={SUBJECT}&limit=20",
        agent="governance-dashboard",
        role="auditor",
    )
    print(f"5. Audit trail contains {len(events)} event(s)")

    deleted = call(
        f"/v1/subjects/{SUBJECT}/memories",
        method="DELETE",
        agent="privacy-admin",
        role="admin",
    )
    print(f"6. Right to be Forgotten deleted {deleted['deleted_count']} record(s)")

    after_delete = call(
        "/v1/memories/search",
        method="POST",
        agent="sales-agent-claude",
        role="sales",
        body={"subject_id": SUBJECT, "limit": 10},
    )
    assert not after_delete["results"], "Deleted memories must not be retrievable"
    print("7. Verification passed: no deleted memory can be retrieved\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Demo failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
