"""Add Juan's September 28 and 29, 2026 Daily reports to Firestore once.

Run from Juan's authenticated Google Cloud Shell. Does not modify existing reports.
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
    "2026-09-28": "Advanced the Boomyard Projects app and website, and tested the features completed so far.",
    "2026-09-29": "Continued improving the Boomyard Projects app and website, and tested the updated features.",
}
NEXT = "Continue testing the app and make adjustments based on the results."


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


def list_docs(collection, token):
    results, page = [], ""
    while True:
        params = urllib.parse.urlencode({"pageSize": 300, "pageToken": page})
        response = request(f"{ROOT}/{collection}?{params}", token)
        results.extend(response.get("documents", []))
        page = response.get("nextPageToken", "")
        if not page:
            return results


def string(fields, key):
    return fields.get(key, {}).get("stringValue", "")


def visible_owner_report(fields, day, uid):
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
        "nextSteps": text(NEXT),
        "blockers": text("None"),
        "hours": {"doubleValue": 8.5},
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
        users = list_docs("users", token)
        owners = [user["name"].rsplit("/", 1)[-1] for user in users
                  if string(user.get("fields", {}), "email").lower() == OWNER_EMAIL]
        if len(owners) != 1:
            raise RuntimeError(f"Expected one matching owner profile, found {len(owners)}. No reports were created.")
        uid = owners[0]
        for day, accomplished in REPORTS.items():
            existing = list_docs("dailyReports", token)
            if any(visible_owner_report(item.get("fields", {}), day, uid) for item in existing):
                print(f"{day}: already exists; left unchanged")
                continue
            base = f"owner-{day}"
            names = {item["name"].rsplit("/", 1)[-1] for item in existing}
            doc_id = base if base not in names else f"{base}-manual"
            if doc_id in names:
                raise RuntimeError(f"{day}: both reserved document IDs exist; stopped to avoid a duplicate")
            url = f"{ROOT}/dailyReports?" + urllib.parse.urlencode({"documentId": doc_id})
            created = request(url, token, document(day, accomplished, uid))
            print(f"{day}: created {created['name'].rsplit('/', 1)[-1]} (8.5 hours)")
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
