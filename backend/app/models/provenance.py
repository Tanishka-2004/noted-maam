import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class TranscriptSegmentRef(BaseModel):
    utterance_id: str
    start_time: float
    end_time: float
    speaker_tag: str
    speaker_name: Optional[str] = None
    text: str

class ExtractorInfo(BaseModel):
    model_name: str = "whisper-v3"
    extractor_version: str = "actions-v3.1"
    prompt_version: str = "v2.1"
    extraction_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ImmutableProvenance(BaseModel):
    meeting_id: str
    workspace_id: str
    primary_project_id: Optional[str] = None
    segments: List[TranscriptSegmentRef] = Field(default_factory=list)
    time_range: str  # e.g., "32:18-34:02"
    speakers_involved: List[str] = Field(default_factory=list)
    primary_quote: str
    extractor: ExtractorInfo = Field(default_factory=ExtractorInfo)
