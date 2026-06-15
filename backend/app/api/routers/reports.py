import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import require_manager
from backend.app.core.database import get_db
from backend.app.crud.task import list_tasks
from backend.app.models.user import User
from backend.app.services.reporting import build_task_report_stats

router = APIRouter(prefix="/reports", tags=["reports"])


async def _fetch_report_tasks(
    db: AsyncSession,
    manager: User,
    date_from: datetime | None,
    date_to: datetime | None,
):
    return await list_tasks(
        db,
        user=manager,
        date_from=date_from,
        date_to=date_to,
        skip=0,
        limit=10000,
    )


@router.get("/tasks/csv")
async def tasks_report_csv(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_manager),
) -> Response:
    items, _ = await _fetch_report_tasks(db, manager, date_from, date_to)
    stats = build_task_report_stats(items, now=datetime.now(tz=date_from.tzinfo if date_from else None))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    writer.writerow(["created", stats["created"]])
    writer.writerow(["completed_on_time", stats["completed_on_time"]])
    writer.writerow(["overdue", stats["overdue"]])
    writer.writerow([])
    writer.writerow(["id", "title", "status", "deadline", "assignee"])
    for t in items:
        writer.writerow([
            t.id,
            t.title,
            t.status.value,
            t.deadline.isoformat() if t.deadline else "",
            t.assignee.full_name if t.assignee else "",
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_report.csv"},
    )


@router.get("/tasks/pdf")
async def tasks_report_pdf(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_manager),
) -> Response:
    items, _ = await _fetch_report_tasks(db, manager, date_from, date_to)
    stats = build_task_report_stats(items, now=datetime.now(tz=date_from.tzinfo if date_from else None))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "TaskMaster — Task Report")
    y -= 1 * cm

    pdf.setFont("Helvetica", 11)
    pdf.drawString(2 * cm, y, f"Created tasks: {stats['created']}")
    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Completed on time: {stats['completed_on_time']}")
    y -= 0.6 * cm
    pdf.drawString(2 * cm, y, f"Overdue: {stats['overdue']}")
    y -= 1 * cm

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "Tasks")
    y -= 0.8 * cm
    pdf.setFont("Helvetica", 9)

    for task in items[:40]:
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm
            pdf.setFont("Helvetica", 9)
        line = (
            f"#{task.id} {task.title[:50]} | {task.status.value} | "
            f"{task.assignee.full_name if task.assignee else '-'}"
        )
        pdf.drawString(2 * cm, y, line)
        y -= 0.5 * cm

    pdf.save()
    buffer.seek(0)
    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tasks_report.pdf"},
    )
