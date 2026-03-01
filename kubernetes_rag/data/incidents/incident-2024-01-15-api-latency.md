# Incident: API Latency Spike — 2024-01-15

## Summary
Production API experienced 5-10x latency increase for 45 minutes. P99 latency rose from 200ms to 2s.

## Timeline (UTC)

| Time | Event |
|------|-------|
| 14:32 | First alerts: API latency P99 > 1s |
| 14:35 | On-call acknowledged, started investigation |
| 14:38 | Identified: etcd compaction lag on control plane |
| 14:42 | Applied etcd defragmentation (maintenance window) |
| 15:05 | Latency returned to baseline |
| 15:15 | Incident resolved |

## Root Cause
etcd database on Kubernetes control plane had accumulated compaction lag. API server requests to etcd were queuing, causing cascading latency across all API operations.

## Resolution
1. Coordinated with platform team for etcd maintenance
2. Ran `etcdctl defrag` on each etcd member during rolling window
3. Monitored API latency until stable

## Post-Incident
- **Action**: Enable automated etcd compaction monitoring
- **Action**: Document etcd defrag procedure in runbooks
- **Follow-up**: Review etcd storage quota and retention settings

## References
- Runbook: etcd maintenance
- Kubernetes: etcd compaction
