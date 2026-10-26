from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class CPGRAMSAdapter(ABC):
    """
    Abstract adapter for CPGRAMS grievance intake.
    Allows swapping file-based demo adapter with a live API client without changing callers.
    """

    @abstractmethod
    def fetch_new_grievances(self) -> List[Dict[str, Any]]:
        """
        Fetch new grievances from CPGRAMS source.
        Returns normalized list of dicts with keys:
          - external_reference (CPGRAMS registration number)
          - complainant_name
          - complainant_email
          - complainant_mobile
          - institution_name_or_id
          - subject
          - description
          - date_received
        """
        raise NotImplementedError


class FileCPGRAMSAdapter(CPGRAMSAdapter):
    """
    File-based implementation of CPGRAMS adapter for demos, testing, and offline imports.
    Supports CSV and JSON files.
    """

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def fetch_new_grievances(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        suffix = self.file_path.suffix.lower()
        if suffix == ".json":
            return self._parse_json()
        elif suffix == ".csv":
            return self._parse_csv()
        return []

    def _parse_json(self) -> List[Dict[str, Any]]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [self._normalize_dict(item) for item in data]
            elif isinstance(data, dict) and "grievances" in data:
                return [self._normalize_dict(item) for item in data["grievances"]]
        return []

    def _parse_csv(self) -> List[Dict[str, Any]]:
        records = []
        with open(self.file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(self._normalize_dict(row))
        return records

    def _normalize_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "external_reference": str(
                row.get("external_reference")
                or row.get("registration_number")
                or row.get("reg_no")
                or ""
            ).strip(),
            "complainant_name": str(
                row.get("complainant_name") or row.get("name") or "CPGRAMS Citizen"
            ).strip(),
            "complainant_email": str(
                row.get("complainant_email") or row.get("email") or ""
            ).strip().lower(),
            "complainant_mobile": str(
                row.get("complainant_mobile") or row.get("mobile") or ""
            ).strip(),
            "institution_name_or_id": str(
                row.get("institution_name_or_id")
                or row.get("institution")
                or row.get("aicte_id")
                or ""
            ).strip(),
            "subject": str(row.get("subject") or "CPGRAMS Grievance").strip(),
            "description": str(row.get("description") or "").strip(),
            "date_received": row.get("date_received"),
        }
