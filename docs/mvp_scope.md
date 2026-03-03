# MVP Scope

## MVP

### 1. URL submission + scan session creation
- Users can submit a valid URL from the dashboard and trigger a new scan session.
- System validates URL format and rejects malformed inputs with clear error messaging.
- A unique scan session ID is created and stored for each accepted submission.

**Acceptance criteria**
- 95% of valid URL submissions create a scan session successfully on first attempt in staging.
- Invalid URL inputs are rejected in under 1 second with an actionable validation message.
- Session creation API responds within 2 seconds (p95) under baseline load.

### 2. 2–3 analyzers (headers, basic performance, DNS)
- MVP includes exactly three analyzers:
  - HTTP header analyzer (e.g., key security and cache headers).
  - Basic performance analyzer (e.g., TTFB, total response time, payload size).
  - DNS analyzer (e.g., record resolution and lookup latency).
- Each analyzer runs in a single scan session and returns structured findings.

**Acceptance criteria**
- At least 99% of scan sessions run all three analyzers without system error.
- Analyzer outputs are stored in a normalized schema with no missing required fields.
- End-to-end scan for a baseline target completes in 15 seconds or less (p95).

### 3. Real-time progress stream
- Users can view scan progress updates in real time from start to completion.
- Progress stream includes at minimum: queued, running analyzer states, and completed/failed terminal state.

**Acceptance criteria**
- Progress events are delivered to connected clients within 1 second of state change (p95).
- 99% of scan sessions emit at least one event per lifecycle stage reached.
- If stream disconnects, client can recover current state within 3 seconds via reconnect.

### 4. Aggregated score + findings list on dashboard
- Dashboard displays one aggregated scan score and a consolidated findings list.
- Findings include severity, analyzer source, and concise remediation guidance.

**Acceptance criteria**
- Aggregated score and findings render within 2 seconds after scan completion (p95).
- 100% of findings shown on dashboard are traceable to analyzer output records.
- Severity labels are present for 100% of findings displayed.

### 5. Persisted scan history
- Completed scan sessions are stored and retrievable in scan history.
- History view includes URL, timestamp, status, and aggregated score.

**Acceptance criteria**
- New completed scans appear in history within 2 seconds of completion (p95).
- History retrieval returns the latest 50 scans in under 1.5 seconds (p95).
- Persisted scan records remain queryable for at least 30 days in MVP environment.

## Post-MVP
The following are explicitly deferred beyond MVP:
- Load testing integrations (k6/Locust).
- Endpoint graph visualization.
- Advanced mistake detection.
- Multi-site monitoring.
