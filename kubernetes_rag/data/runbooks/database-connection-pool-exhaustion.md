# Runbook: Database Connection Pool Exhaustion

## Overview
Resolve database connection pool exhaustion affecting application pods.

## Symptoms
- Application logs: "connection pool exhausted", "too many connections"
- Database metrics: high connection count, connection timeouts
- 503 errors or slow response times from dependent services

## Prerequisites
- Access to application and database metrics (Prometheus/Grafana)
- Database admin credentials for connection inspection

## Procedure

### Step 1: Confirm the Issue
```bash
# Check application pod logs
kubectl logs -l app=myapp -n production --tail=500 | grep -i "connection\|pool"

# Database connection count (PostgreSQL example)
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Step 2: Identify Leaking Connections
- Review connection pool settings: `max_connections`, `pool_size`
- Check for connection leaks in application code (unclosed connections)
- Look for long-running queries blocking connections

### Step 3: Immediate Mitigation
1. **Scale up** application replicas to spread load (if pool is per-pod)
2. **Restart** affected pods to clear stuck connections (last resort)
3. **Kill idle** connections on database side if safe

### Step 4: Root Cause Fix
- Increase pool size if legitimate load growth
- Fix connection leak in application (ensure `close()` or context managers)
- Add connection timeout and health checks

## Prevention
- Set appropriate `max_connections` and `pool_size`
- Use connection pooler (PgBouncer, ProxySQL) for high connection counts
- Monitor `pg_stat_activity` or equivalent metrics

## Escalation
Escalate to DBA team if database-side changes required.
