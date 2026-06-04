"""
Pydantic models for Backrest connect-rpc API responses.

Field names use camelCase to match the connect-rpc JSON encoding (proto field names).
Use model_config = ConfigDict(populate_by_name=True) if snake_case access is needed
after testing against a live instance.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Operation(BaseModel):
    id: Optional[str] = None
    planId: Optional[str] = None
    repoId: Optional[str] = None
    status: Optional[str] = None
    unixTimeStartMs: Optional[int] = None
    unixTimeEndMs: Optional[int] = None
    displayMessage: Optional[str] = None


class OperationList(BaseModel):
    operations: List[Operation] = []


class Snapshot(BaseModel):
    id: Optional[str] = None
    unixTimeMs: Optional[int] = None
    hostname: Optional[str] = None
    paths: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class SnapshotList(BaseModel):
    snapshots: List[Snapshot] = []


class LsEntry(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    mtime: Optional[str] = None


class ListSnapshotFilesResponse(BaseModel):
    path: Optional[str] = None
    entries: List[LsEntry] = []


class PlanSummary(BaseModel):
    id: Optional[str] = None
    backupsFailedLast30days: Optional[int] = None
    backupsSuccessLast30days: Optional[int] = None
    bytesAddedLast30days: Optional[int] = None
    totalSnapshots: Optional[int] = None
    nextBackupTimeMs: Optional[int] = None


class SummaryDashboard(BaseModel):
    repoSummaries: List[PlanSummary] = []
    planSummaries: List[PlanSummary] = []
    configPath: Optional[str] = None
    dataPath: Optional[str] = None
