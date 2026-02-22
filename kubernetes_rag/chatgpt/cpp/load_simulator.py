#!/usr/bin/env python3
"""Load simulator — fires concurrent requests at the ChatGPT backend.

Usage:
    python load_simulator.py --url http://localhost:8000 --concurrency 20 --total 200

Measures:
    - p50 / p95 / p99 latency
    - Throughput (req/s)
    - Error rate
    - Token throughput (tokens/s)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import List

import aiohttp


@dataclass
class RequestResult:
    latency_ms: float
    status: int
    tokens: int = 0
    error: str = ""


@dataclass
class LoadTestReport:
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    total_tokens: int = 0
    elapsed_s: float = 0

    def summary(self) -> str:
        latencies = sorted(self.latencies) if self.latencies else [0]

        def pct(p: float) -> float:
            idx = int(p * len(latencies))
            idx = min(idx, len(latencies) - 1)
            return latencies[idx]

        throughput = self.successful / self.elapsed_s if self.elapsed_s > 0 else 0
        token_rate = self.total_tokens / self.elapsed_s if self.elapsed_s > 0 else 0
        error_pct = (self.failed / self.total_requests * 100) if self.total_requests else 0

        return (
            f"\n{'=' * 50}\n"
            f"  Load Test Results\n"
            f"{'=' * 50}\n"
            f"  Total requests:  {self.total_requests}\n"
            f"  Successful:      {self.successful}\n"
            f"  Failed:          {self.failed} ({error_pct:.1f}%)\n"
            f"  Elapsed:         {self.elapsed_s:.1f}s\n"
            f"  Throughput:      {throughput:.1f} req/s\n"
            f"  Token rate:      {token_rate:.0f} tokens/s\n"
            f"\n  Latency:\n"
            f"    p50:  {pct(0.50):.1f} ms\n"
            f"    p95:  {pct(0.95):.1f} ms\n"
            f"    p99:  {pct(0.99):.1f} ms\n"
            f"    mean: {statistics.mean(latencies):.1f} ms\n"
            f"    max:  {max(latencies):.1f} ms\n"
            f"{'=' * 50}\n"
        )


SAMPLE_QUERIES = [
    "What is a Kubernetes Pod?",
    "Explain Docker networking",
    "How does etcd work in Kubernetes?",
    "What is a DaemonSet?",
    "Describe Kubernetes RBAC",
    "How do Persistent Volumes work?",
    "What is a Service Mesh?",
    "Explain Helm charts",
    "What is container orchestration?",
    "How does HPA work in Kubernetes?",
]


async def send_request(
    session: aiohttp.ClientSession,
    url: str,
    query: str,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        t0 = time.perf_counter()
        try:
            payload = {"message": query, "max_tokens": 256}
            async with session.post(
                f"{url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                body = await resp.json()
                latency = (time.perf_counter() - t0) * 1000
                tokens = body.get("usage", {}).get("total", 0)
                return RequestResult(
                    latency_ms=latency,
                    status=resp.status,
                    tokens=tokens,
                )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return RequestResult(latency_ms=latency, status=0, error=str(exc))


async def run_load_test(url: str, concurrency: int, total: int) -> LoadTestReport:
    semaphore = asyncio.Semaphore(concurrency)
    report = LoadTestReport()

    queries = [SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)] for i in range(total)]

    t0 = time.perf_counter()

    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session, url, q, semaphore) for q in queries]
        results = await asyncio.gather(*tasks)

    report.elapsed_s = time.perf_counter() - t0
    report.total_requests = total

    for r in results:
        if r.status == 200 and not r.error:
            report.successful += 1
            report.latencies.append(r.latency_ms)
            report.total_tokens += r.tokens
        else:
            report.failed += 1

    return report


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Backend Load Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--concurrency", type=int, default=20, help="Max concurrent requests")
    parser.add_argument("--total", type=int, default=200, help="Total requests to send")
    args = parser.parse_args()

    print(f"Starting load test: url={args.url} concurrency={args.concurrency} total={args.total}")

    report = asyncio.run(run_load_test(args.url, args.concurrency, args.total))
    print(report.summary())


if __name__ == "__main__":
    main()
