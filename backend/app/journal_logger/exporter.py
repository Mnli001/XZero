"""CSV / Excel export (MTCS-journal compatible columns)."""
from __future__ import annotations

import csv
import io

COLUMNS = ["journaled_at", "kind", "symbol", "side", "lots", "entry", "exit_price",
           "sl", "tp", "pnl", "r_multiple", "confidence", "reason", "exit_reason"]


def _flat(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        flat = {c: r.get(c, "") for c in COLUMNS}
        flat["checklist"] = str(r.get("checklist", r.get("explanation", "")))
        flat["reasoning"] = str(r.get("reasoning", ""))
        out.append(flat)
    return out


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    cols = COLUMNS + ["checklist", "reasoning"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in _flat(rows):
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def to_excel(rows: list[dict]) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "journal"
    cols = COLUMNS + ["checklist", "reasoning"]
    ws.append(cols)
    for r in _flat(rows):
        ws.append([r.get(c, "") for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
