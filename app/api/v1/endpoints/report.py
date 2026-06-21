from fastapi import APIRouter, HTTPException

router = APIRouter()

_reports:dict[str, dict] = {}

def save_report(report_id:str,data: dict) -> None:
    _reports[report_id] = data

@router.get("/")
async def list_reports():
    return {
        "total" : len(_reports),
        "reports_ids" : list(_reports.keys()),
    }

@router.get("/{report_id}")
async def get_report(report_id:str):
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return report

@router.delete("/{report_id}")
async def delete_report(report_id:str):
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    del _reports[report_id]
    return {"deleted" : report_id}
