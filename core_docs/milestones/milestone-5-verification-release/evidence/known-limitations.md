# Known limitations and release exceptions

Review this file for every candidate. A limitation documents scope or residual risk; it does not turn
a failed Must requirement into a pass. Link failures to the verification report and keep the release
blocked until Must criteria pass or the governing specification is formally changed.

## Product limitations

- This is a single-person, single-laptop academic assistive prototype, not a medical device,
  diagnostic tool, guaranteed fall detector, or substitute for a caregiver/emergency service.
- Sensor input is replayed from public datasets rather than a validated physical wearable.
- Recognition depends on camera visibility/angle/lighting, dataset representativeness, the selected
  model or deterministic fallback, and frozen thresholds.
- A critical fall normally requires correlated sensor motion and horizontal video evidence; a true
  incident seen by only one modality may not create a critical fall event.
- The deterministic sensor and feedback fallbacks preserve operation but do not imply equivalent
  recognition or language quality to an approved local model.
- Webcam passthrough is host-dependent. The Compose overlay targets Linux; macOS and Windows require
  the documented host-run Video Service fallback.
- The local broker uses trusted-laptop development defaults. MQTT authentication/TLS and production
  hardening are required before use outside a local trusted environment.
- Datasets and model weights are not distributed in Git; they must be prepared, licensed, pinned,
  and hashed before an offline run.
- Stored activity/history reflects accepted inputs and bounded continuity rules, not clinical truth.

## Candidate-specific exceptions

| ID | Finding/failed criterion | Requirement | Severity / user impact | Accepted by / expiry | Mitigation and retest | Status |
|---|---|---|---|---|---|---|
| `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `OPEN` |

If there are no candidate-specific exceptions, replace the placeholder with “None” plus reviewer and
UTC timestamp. Never delete historical failed-result artifacts.

