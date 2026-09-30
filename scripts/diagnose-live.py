"""Read-only check of the Firebase project from an authenticated Google Cloud Shell.

Prints rule version and document counts/dates, never credentials or report content.
"""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = "boomyard-projects"
BASE = f"projects/{PROJECT}/databases/(default)/documents"


def fetch(url, token, data=None):
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error).get("error", {}).get("message", "")
        except (ValueError, OSError):
            detail = ""
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error


def all_documents(name, token):
    documents = []
    page = ""
    while True:
        query = urllib.parse.urlencode({"pageSize": 300, "pageToken": page})
        result = fetch(f"https://firestore.googleapis.com/v1/{BASE}/{name}?{query}", token)
        documents.extend(result.get("documents", []))
        page = result.get("nextPageToken", "")
        if not page:
            return documents


def value(fields, name):
    entry = fields.get(name, {})
    return next(iter(entry.values()), None)


def main():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True, stderr=subprocess.PIPE).strip()
    except (OSError, subprocess.CalledProcessError):
        print("ERROR: Google Cloud Shell is not authenticated for this project.")
        return 1
    print(f"Project: {PROJECT}")
    local_rules = Path(__file__).resolve().parents[1] / "firestore.rules"
    try:
        release = fetch(f"https://firebaserules.googleapis.com/v1/projects/{PROJECT}/releases/cloud.firestore", token)
        ruleset = fetch(f"https://firebaserules.googleapis.com/v1/{release['rulesetName']}", token)
        live_rules = "\n".join(item.get("content", "") for item in ruleset.get("source", {}).get("files", []))
        same = local_rules.exists() and live_rules.strip() == local_rules.read_text().strip()
        print(f"Firestore rules: {'MATCH repo' if same else 'DIFFER from repo'}")
        print(f"Active rules release: {release.get('rulesetName', 'unknown')}")
        print(f"Live rules SHA256: {hashlib.sha256(live_rules.strip().encode()).hexdigest()[:16]}")
        print(f"Live dailyReports read for signed-in users: {('allow get, list: if signedIn();' in live_rules)}")
        goals_read = "match /goals/{id} {\n      allow read: if signedIn();" in live_rules
        print(f"Live goals read for signed-in users: {goals_read}")
    except (KeyError, RuntimeError) as error:
        print(f"Rules check failed: {error}")

    for collection in ("dailyReports", "projects", "tasks", "goals", "feedback"):
        try:
            docs = all_documents(collection, token)
        except RuntimeError as error:
            print(f"{collection}: ERROR {error}")
            continue
        deleted = sum(value(doc.get("fields", {}), "deletedAt") is not None for doc in docs)
        print(f"{collection}: {len(docs)} documents ({deleted} marked deleted)")
        if collection == "dailyReports":
            for doc in docs:
                fields = doc.get("fields", {})
                day = value(fields, "reportDate") or "no reportDate"
                print(f"  {doc['name'].rsplit('/', 1)[-1]} | {day} | deleted={value(fields, 'deletedAt') is not None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
