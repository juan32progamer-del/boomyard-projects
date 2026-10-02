"""Add Juan's September 30 and October 1, 2026 Daily reports once.

Run in Juan's authenticated Google Cloud Shell. Existing reports are not changed.
"""
import datetime as dt
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

PROJECT = "boomyard-projects"
OWNER_EMAIL = "juan32progamer@gmail.com"
ROOT = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
REPORTS = {
    "2026-09-30": "Fixed issues in the Boomyard Projects app and tested the changes.",
    "2026-10-01": "Started working on Alex's project and continued checking the Boomyard Projects app.",
}


def request(url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = json.load(error).get("error", {}).get("message", "")
        except (ValueError, OSError):
            pass
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error


def list_docs(token):
    results, page = [], ""
    while True:
        params = urllib.parse.urlencode({"pageSize": 300, "pageToken": page})
        response = request(f"{ROOT}/dailyReports?{params}", token)
        results.extend(response.get("documents", []))
        page = response.get("nextPageToken", "")
        if not page:
            return results


def string(fields, key):
    return fields.get(key, {}).get("stringValue", "")


def owner_report(fields, day, uid):
    owner = (string(fields, "authorEmail").lower() == OWNER_EMAIL
             or string(fields, "createdBy").lower() == OWNER_EMAIL
             or uid and string(fields, "authorUid") == uid)
    deleted = "deletedAt" in fields and "nullValue" not in fields["deletedAt"]
    return owner and string(fields, "reportDate") == day and not deleted


def document(day, accomplished, uid):
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    text = lambda value: {"stringValue": value}
    fields = {
        "reportDate": text(day),
        "accomplished": text(accomplished),
        "nextSteps": text("Continue improving the app and advancing Alex's project."),
        "blockers": text("None"),
        "author": text("Juan Chahin"),
        "authorEmail": text(OWNER_EMAIL),
        "createdBy": text(OWNER_EMAIL),
        "createdAt": {"timestampValue": now},
    }
    if uid:
        fields["authorUid"] = text(uid)
    return {"fields": fields}


def main():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True, stderr=subprocess.PIPE).strip()
        existing = list_docs(token)
        owner_uids = {string(report.get("fields", {}), "authorUid")
                      for report in existing
                      if string(report.get("fields", {}), "authorEmail").lower() == OWNER_EMAIL
                      or string(report.get("fields", {}), "createdBy").lower() == OWNER_EMAIL}
        owner_uids.discard("")
        uid = next(iter(owner_uids)) if len(owner_uids) == 1 else ""
        for day, accomplished in REPORTS.items():
            existing = list_docs(token)
            if any(owner_report(item.get("fields", {}), day, uid) for item in existing):
                print(f"{day}: already exists; left unchanged")
                continue
            base = f"owner-{day}"
            names = {item["name"].rsplit("/", 1)[-1] for item in existing}
            doc_id = base if base not in names else f"{base}-manual"
            if doc_id in names:
                raise RuntimeError(f"{day}: both reserved document IDs exist; stopped to avoid a duplicate")
            url = f"{ROOT}/dailyReports?" + urllib.parse.urlencode({"documentId": doc_id})
            created = request(url, token, document(day, accomplished, uid))
            print(f"{day}: created {created['name'].rsplit('/', 1)[-1]}")
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
