# Dependency, license, cost, and offline inventory

**Status:** `NOT RUN`  
**Candidate commit / UTC time:** `PENDING`  
**Inventory command/tool version:** `PENDING`  
**Reviewer role:** `PENDING`

Generate inventories from the exact release locks, container images, model files, dataset versions,
and target-laptop tooling. Do not assume a package is approved because it is free to download. Record
the license source, redistribution/use constraints, runtime network need, and decision for every
direct dependency; preserve a complete transitive inventory as an artifact.

Run the dependency/pin and release audits from the repository root and link their outputs here:

```bash
uv run python scripts/validate_deployment.py
uv run python scripts/release_audit.py --output-dir artifacts/release
```

Repeat the release audit with `--runtime-path <sanitized-log-or-artifact-directory>` for every
exported runtime evidence directory. To include live database fields, export the local host
`DATABASE_URL` without printing it, then pass `--database-url "$DATABASE_URL"`. Also inspect
`requirements.txt`, `requirements-dev.txt`,
`uv.lock`, `dashboard/package-lock.json`, Compose image digests, Docker base images, Mosquitto config,
the configured sensor model's license, Ollama/model license, and all evaluation datasets.

## Runtime component decisions

| Component/source | Pinned version/digest/revision | License and authoritative source | Paid/cloud/runtime network required | Approved? | Artifact/notes |
|---|---|---|---|---|---|
| HAR Python application | `PENDING` | Project license: `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Python runtime and direct dependencies | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Dashboard and direct dependencies | `PENDING` | `PENDING` | `PENDING` | `NOT RUN` | `PENDING` |
| Backend base image | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| Dashboard/Nginx base image | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| PostgreSQL image | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| Eclipse Mosquitto image | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| Sensor model or deterministic fallback | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| MediaPipe pose model/package | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| Ollama executable/model or deterministic fallback | `PENDING` | `PENDING` | No after preparation: verify | `NOT RUN` | `PENDING` |
| UCI HAR evaluation dataset | `PENDING` | `PENDING` | Download only during preparation | `NOT RUN` | `PENDING` |
| WISDM evaluation dataset, if used | `PENDING` | `PENDING` | Download only during preparation | `NOT RUN` | `PENDING` |
| SisFall evaluation dataset, if used | `PENDING` | `PENDING` | Download only during preparation | `NOT RUN` | `PENDING` |

## Inventory artifacts

| Artifact | Generator/command | Hash/path | Review status |
|---|---|---|---|
| Python resolved dependency inventory | `PENDING` | `PENDING` | `NOT RUN` |
| Dashboard resolved dependency inventory | `PENDING` | `PENDING` | `NOT RUN` |
| Container/base image digest inventory | `PENDING` | `PENDING` | `NOT RUN` |
| Dataset/model file hash inventory | `PENDING` | `PENDING` | `NOT RUN` |
| Secret/prohibited-artifact scan | `PENDING` | `PENDING` | `NOT RUN` |
| License exceptions/approvals | `PENDING` | `PENDING` | `NOT RUN` |

**Unresolved, paid, closed, or runtime-cloud dependency count:** `PENDING`  
**NFR-7 decision:** `NOT RUN`  
**Reviewer sign-off:** `PENDING`
