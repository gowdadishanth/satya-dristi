from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ReportListItem(BaseModel):
    report_id: str
    analysis_id: str
    uid: str
    query: str
    task: str
    input: str
    date: str
    time: str
    confidence: str
    status: str
    answer: str
    generated_at: str
    pdf_filename: Optional[str] = None
    json_filename: Optional[str] = None

class ReportDetailResponse(ReportListItem):
    pdf_path: Optional[str] = None
    json_path: Optional[str] = None
