# Milestone 3 implementation notes

The Fusion service is the authoritative owner of activity and safety state.

- `services/fusion_service/fusion.py` keeps bounded, timestamp-ordered modality buffers, rejects
  duplicate/late messages, aligns nearest fresh samples, performs normalized weight × confidence
  voting, and applies a rolling majority smoother. The raw winner and displayed stable label remain
  separately observable in diagnostics.
- `services/fusion_service/safety.py` confirms a critical `FALL` only when sensor motion and video
  horizontal evidence correlate. Cooldown plus upright/low-motion recovery (or timeout) prevents
  duplicate alerts. Inactivity is one-shot until meaningful motion resets it. The optional abnormal
  rule is deliberately explainable: a run exceeding an absolute minimum and a multiple of its recent
  median duration raises a warning.
- `services/fusion_service/runtime.py` subscribes to both prediction topics with QoS 1, resubscribes
  after reconnect, persists before best-effort MQTT/WebSocket publication, and keeps a bounded retry
  queue for temporary database failures. Payload validation failures never terminate the consumer.
- `shared/sql/001_init.sql` installs repeatable uniqueness indexes for interval/event timestamps;
  inserts use `ON CONFLICT` so QoS-1 retries and restarts do not duplicate history. The Fusion startup
  applies this migration to existing development volumes as well as fresh databases.
- REST range queries require UTC timestamps and deterministic chronological ordering. Acknowledgement
  is idempotent for an existing event and returns not-found only for an unknown ID. WebSocket clients
  have bounded queues; a stalled client is dropped without blocking safety processing.

Database records are authoritative because PostgreSQL and MQTT cannot share an atomic transaction in
this deployment. Delivery failures are surfaced through health/status and structured counters.

