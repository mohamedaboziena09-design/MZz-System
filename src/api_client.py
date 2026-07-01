"""
src/api_client.py
==================
API Client Layer — V2.1
طبقة الاتصال بالـ FastAPI.

المبدأ:
    - في V1 (Desktop): يعمل مع CRUDService مباشرة (offline)
    - في V2 (Web):     يعمل مع FastAPI عبر HTTP

الاستخدام:
    client = APIClient.from_workspace(ctx)

    # كل الشاشات تستخدم نفس الواجهة:
    emps = client.employees.list(status="active")
    emp  = client.employees.get(1)
    emp  = client.employees.create({...})
    emp  = client.employees.update(1, {...})
           client.employees.delete(1)
"""

from __future__ import annotations

import json
import pathlib
import urllib.request
import urllib.error
import urllib.parse
from base64    import b64encode
from typing    import Any, Optional


# ════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════

class APIError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"[{status}] {detail}")

class AuthError(APIError):
    pass

class NotFoundError(APIError):
    pass

class ConflictError(APIError):
    pass

class ConnectionError(APIError):
    pass


# ════════════════════════════════════════════════════════════
# HTTP Transport
# ════════════════════════════════════════════════════════════

class _Transport:
    """
    طبقة HTTP خفيفة بدون مكتبات خارجية.
    تستخدم urllib فقط.
    """

    def __init__(self, base_url: str, username: str, password: str,
                 timeout: int = 10) -> None:
        self._base    = base_url.rstrip("/")
        self._auth    = b64encode(f"{username}:{password}".encode()).decode()
        self._timeout = timeout

    def _headers(self, extra: dict = None) -> dict:
        h = {
            "Authorization": f"Basic {self._auth}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def request(self, method: str, path: str,
                body: Any = None, params: dict = None) -> Any:
        url = self._base + path
        if params:
            url += "?" + urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(
            url, data=data, headers=self._headers(), method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            raw    = e.read().decode()
            detail = raw
            try:
                detail = json.loads(raw).get("detail", raw)
            except Exception:
                pass
            if e.code == 401: raise AuthError(401, detail)
            if e.code == 404: raise NotFoundError(404, detail)
            if e.code == 409: raise ConflictError(409, detail)
            raise APIError(e.code, detail)
        except urllib.error.URLError as e:
            raise ConnectionError(0, f"تعذر الاتصال بالـ API: {e.reason}")

    def get(self, path: str, params: dict = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any) -> Any:
        return self.request("POST", path, body=body)

    def put(self, path: str, body: Any) -> Any:
        return self.request("PUT", path, body=body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def upload_file(self, path: str, field: str,
                    file_path: pathlib.Path, extra_fields: dict = None) -> Any:
        """رفع ملف بـ multipart/form-data."""
        import uuid
        boundary = uuid.uuid4().hex
        body_parts = []

        # Extra fields
        for key, val in (extra_fields or {}).items():
            body_parts.append(
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f'{val}\r\n'
            )

        # File
        fname   = file_path.name
        content = file_path.read_bytes()
        body_parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{field}"; filename="{fname}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        )
        body_bytes = (
            "".join(body_parts).encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )

        headers = self._headers({
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        })
        del headers["Content-Type"]
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        url = self._base + path
        req = urllib.request.Request(url, data=body_bytes,
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            raise APIError(e.code, detail)

    def ping(self) -> bool:
        """تحقق من الاتصال بالـ API."""
        try:
            self.get("/")
            return True
        except Exception:
            return False


# ════════════════════════════════════════════════════════════
# Resource Base
# ════════════════════════════════════════════════════════════

class _Resource:
    def __init__(self, transport: _Transport) -> None:
        self._t = transport


# ════════════════════════════════════════════════════════════
# Employees Resource
# ════════════════════════════════════════════════════════════

class _EmployeesResource(_Resource):

    def list(self, search: str = None, department: str = None,
             status: str = None, limit: int = 50,
             offset: int = 0) -> dict:
        return self._t.get("/employees", params=dict(
            search=search, department=department,
            status=status, limit=limit, offset=offset,
        ))

    def get(self, employee_id: int) -> dict:
        return self._t.get(f"/employees/{employee_id}")

    def create(self, data: dict) -> dict:
        return self._t.post("/employees", data)

    def update(self, employee_id: int, data: dict) -> dict:
        return self._t.put(f"/employees/{employee_id}", data)

    def delete(self, employee_id: int) -> dict:
        return self._t.delete(f"/employees/{employee_id}")

    def upload_photo(self, employee_id: int,
                     file_path: pathlib.Path) -> dict:
        return self._t.upload_file(
            f"/employees/{employee_id}/photo", "file", file_path
        )

    def list_documents(self, employee_id: int) -> list:
        return self._t.get(f"/employees/{employee_id}/documents")

    def upload_document(self, employee_id: int,
                        file_path: pathlib.Path,
                        document_type: str,
                        notes: str = None) -> dict:
        return self._t.upload_file(
            f"/employees/{employee_id}/documents", "file", file_path,
            extra_fields={"document_type": document_type,
                          "notes": notes or ""},
        )

    def delete_document(self, document_id: int) -> dict:
        return self._t.delete(f"/employees/documents/{document_id}")


# ════════════════════════════════════════════════════════════
# Persons Resource
# ════════════════════════════════════════════════════════════

class _PersonsResource(_Resource):

    def list(self, search: str = None, person_type: str = None,
             status: str = None, profile_complete: int = None,
             limit: int = 50, offset: int = 0) -> dict:
        return self._t.get("/persons", params=dict(
            search=search, person_type=person_type,
            status=status, profile_complete=profile_complete,
            limit=limit, offset=offset,
        ))

    def get(self, person_id: int) -> dict:
        return self._t.get(f"/persons/{person_id}")

    def create(self, data: dict) -> dict:
        return self._t.post("/persons", data)

    def update(self, person_id: int, data: dict) -> dict:
        return self._t.put(f"/persons/{person_id}", data)

    def delete(self, person_id: int) -> dict:
        return self._t.delete(f"/persons/{person_id}")

    def upload_photo(self, person_id: int,
                     file_path: pathlib.Path) -> dict:
        return self._t.upload_file(
            f"/persons/{person_id}/photo", "file", file_path
        )

    def list_documents(self, person_id: int) -> list:
        return self._t.get(f"/persons/{person_id}/documents")

    def upload_document(self, person_id: int,
                        file_path: pathlib.Path,
                        document_type: str,
                        notes: str = None) -> dict:
        return self._t.upload_file(
            f"/persons/{person_id}/documents", "file", file_path,
            extra_fields={"document_type": document_type,
                          "notes": notes or ""},
        )

    def delete_document(self, document_id: int) -> dict:
        return self._t.delete(f"/persons/documents/{document_id}")


# ════════════════════════════════════════════════════════════
# Vehicles Resource
# ════════════════════════════════════════════════════════════

class _VehiclesResource(_Resource):

    def list(self, status: str = None, vehicle_type: str = None,
             search: str = None, limit: int = 50,
             offset: int = 0) -> dict:
        return self._t.get("/vehicles", params=dict(
            status=status, vehicle_type=vehicle_type,
            search=search, limit=limit, offset=offset,
        ))

    def get(self, vehicle_id: int) -> dict:
        return self._t.get(f"/vehicles/{vehicle_id}")

    def create(self, data: dict) -> dict:
        return self._t.post("/vehicles", data)

    def update(self, vehicle_id: int, data: dict) -> dict:
        return self._t.put(f"/vehicles/{vehicle_id}", data)

    def delete(self, vehicle_id: int) -> dict:
        return self._t.delete(f"/vehicles/{vehicle_id}")

    def assign(self, vehicle_id: int, employee_id: int,
               assigned_date: str, reason: str = None) -> dict:
        return self._t.post("/vehicles/assign", {
            "vehicle_id":    vehicle_id,
            "employee_id":   employee_id,
            "assigned_date": assigned_date,
            "reason":        reason,
        })

    def return_vehicle(self, assignment_id: int,
                       returned_date: str) -> dict:
        return self._t.put(
            f"/vehicles/assign/{assignment_id}/return",
            params={"returned_date": returned_date},
            body=None,
        )

    def list_movements(self, vehicle_id: int,
                       limit: int = 20) -> list:
        return self._t.get(
            f"/vehicles/{vehicle_id}/movements",
            params={"limit": limit},
        )

    def add_movement(self, data: dict) -> dict:
        return self._t.post("/movements", data)


# ════════════════════════════════════════════════════════════
# Dashboard Resource
# ════════════════════════════════════════════════════════════

class _DashboardResource(_Resource):

    def stats(self) -> dict:
        return self._t.get("/stats")

    def search(self, query: str) -> dict:
        return self._t.get("/search", params={"q": query})


# ════════════════════════════════════════════════════════════
# Drivers Resource
# ════════════════════════════════════════════════════════════

class _DriversResource(_Resource):

    def list(self) -> list:
        return self._t.get("/drivers")

    def create(self, data: dict) -> dict:
        return self._t.post("/drivers", data)


# ════════════════════════════════════════════════════════════
# Main APIClient
# ════════════════════════════════════════════════════════════

class APIClient:
    """
    العميل الرئيسي للـ API.

    الاستخدام:
        client = APIClient(
            base_url = "http://127.0.0.1:8000",
            username = "admin",
            password = "secret",
        )
        if client.ping():
            stats = client.dashboard.stats()
            emps  = client.employees.list(status="active")
    """

    def __init__(self, base_url: str, username: str,
                 password: str, timeout: int = 10) -> None:
        self._transport  = _Transport(base_url, username, password, timeout)
        self.employees   = _EmployeesResource(self._transport)
        self.persons     = _PersonsResource(self._transport)
        self.vehicles    = _VehiclesResource(self._transport)
        self.drivers     = _DriversResource(self._transport)
        self.dashboard   = _DashboardResource(self._transport)

    def ping(self) -> bool:
        return self._transport.ping()

    @classmethod
    def from_workspace(cls, ctx) -> "APIClient":
        """
        إنشاء client من WorkspaceContext.
        يقرأ إعدادات الـ API من config.json.
        """
        cfg = ctx.config
        return cls(
            base_url = cfg.get("api_url",  "http://127.0.0.1:8000"),
            username = cfg.get("admin_username", ""),
            password = cfg.get("api_password",  ""),
            timeout  = cfg.get("api_timeout",   10),
        )

    @classmethod
    def from_config(cls, config_path: pathlib.Path) -> "APIClient":
        """إنشاء client من ملف config.json مباشرة."""
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(
            base_url = cfg.get("api_url",  "http://127.0.0.1:8000"),
            username = cfg.get("admin_username", ""),
            password = cfg.get("api_password",  ""),
        )