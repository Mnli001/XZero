"""Journal reads + CSV/Excel export."""
from fastapi import APIRouter, Query
from fastapi.responses import Response

from ..journal_logger import to_csv, to_excel
from ..services import get_journal

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("")
def read_journal(kind: str | None = None, limit: int = Query(500, le=2000)):
    rows = get_journal().read(kind=kind, limit=limit)
    return {"count": len(rows), "rows": rows[::-1]}


@router.get("/export.csv")
def export_csv(kind: str | None = None):
    return Response(to_csv(get_journal().read(kind=kind, limit=5000)),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=xzero_journal.csv"})


@router.get("/export.xlsx")
def export_xlsx(kind: str | None = None):
    return Response(to_excel(get_journal().read(kind=kind, limit=5000)),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=xzero_journal.xlsx"})
