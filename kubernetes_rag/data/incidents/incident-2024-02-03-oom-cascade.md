# Incident: OOM Cascade — 2024-02-03

## Summary
Multiple pods OOMKilled in sequence, causing service degradation. Memory pressure spread across nodes.

## Timeline (UTC)

| Time | Event |
|------|-------|
| 09:15 | First pod OOMKilled in payment-service |
| 09:18 | 3 more pods OOM in same deployment |
| 09:22 | Node memory pressure; kubelet evicting pods |
| 09:25 | Cascading restarts across 2 nodes |
| 09:35 | Scaled up payment-service, added memory limits |
| 09:50 | Cluster stabilized |

## Root Cause
Payment service memory limit (512Mi) was insufficient for peak load. No resource requests caused uneven scheduling; when one pod OOM'd, rescheduling increased load on remaining pods.

## Resolution
1. Scaled deployment from 3 to 5 replicas to spread load
2. Increased memory limit to 1Gi with request 768Mi
3. Added PodDisruptionBudget to prevent full outage during rollout

## Lessons Learned
- Set both requests and limits for production workloads
- Monitor memory usage trends, not just current values
- Use PDBs for critical services

## References
- Runbook: Pod Crash Loop
- Runbook: OOMKilled troubleshooting
