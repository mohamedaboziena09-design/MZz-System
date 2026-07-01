# Future Architecture Decisions

This document records architectural ideas that have been approved conceptually but are intentionally deferred until the appropriate project phase.

---

## V2.1 Storage Manager
Status: Planned

Goal:
- Separate application binaries from user data.
- Allow users to select a workspace directory.
- Create:
  - database/
  - uploads/
  - backups/
  - logs/
  - config/

Reason:
Application updates must never overwrite customer data.

---

## API Client Layer
Status: Deferred

Reason:
Implementation begins after Storage Manager is completed.

---

## Session Management
Status: Deferred

Depends on:
- Authentication
- API Integration

---

## Gate Integration
Status: Future

Depends on:
- Stable API
- Search Engine
- Workspace Architecture

---

## Cloud Synchronization
Status: Future

Depends on:
- Local Workspace
- Backup System