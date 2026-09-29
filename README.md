# Boomyard Projects

Static web app hosted on GitHub Pages and optionally Firebase Hosting. Firebase Authentication, Firestore and Storage hold the team data.

## Access

Google sign-in creates a profile with the `employee` role. The verified owner account is `juan32progamer@gmail.com`. In **Settings → Team access**, the owner can assign `admin`, `lead`, `employee` or `client`. An admin can assign `lead`, `employee` or `client` to another person. A user cannot promote their own role. Existing profiles with a null email or no role are completed on their next sign-in.

| Role | Access |
| --- | --- |
| Owner | All team records, roles, settings and change history |
| Admin | Team Daily reports, projects, tasks, settings, role assignments below admin and history |
| Lead | Projects, tasks and their own Daily reports |
| Employee | Projects, task status and their own Daily reports |
| Client | Assigned projects, photos on those projects and their own feedback |

The client role uses the project's `clientUid`. Assign an existing client account while editing the project. Projects without a client assignment remain invisible to clients. The UI and Firebase rules enforce the same access boundaries.

Daily reports are retrieved without ordering by `createdAt`, so old reports missing that field remain visible. Non-admins query their own reports by `authorUid`, `createdBy` or `authorEmail`; admins query the collection. The archive sorts by report date and can filter by week, fortnight or exact date.

## Change history

Creating, editing and deleting a project, task or Daily report writes an immutable `auditLogs` entry in the same Firestore batch or transaction. The entry records actor, time, action and before/after values. Delete is a soft delete: the record remains in Firestore for audit but disappears from normal views. The history starts when these changes are deployed; previous edits cannot be reconstructed.

## Verify and publish

With Java 17 and Node 20 or 22, run `npm ci` and `npm run test:rules`. These are emulator tests for report ownership, role escalation, client scope, history integrity and file access. The browser app itself needs no build step.

Publishing sequence: publish `index.html` to both hosts used by the team, then deploy `firestore.rules` and `storage.rules` with `firebase deploy --only firestore:rules,storage --project boomyard-projects`. Firebase may ask to enable Firestore access for Storage rules on first deployment. Test a normal employee, a client and an admin before relying on the new rules. GitHub Pages serves from `main` at `/boomyard-projects/`; Firebase Hosting serves from this repository's root. The rule files are included in `firebase.json` and excluded from Hosting output.
