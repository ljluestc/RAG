/**
 * inference_scheduler.cpp — Priority-queue batched inference scheduler.
 *
 * Demonstrates a multi-threaded C++ scheduler that could front-end a
 * GPU inference server.  Requests are enqueued with a priority; worker
 * threads pull batches off the queue and "process" them (simulated).
 *
 * Build:
 *   mkdir build && cd build && cmake .. && make
 *   ./inference_scheduler --workers 4 --batch 8 --requests 200
 */

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <numeric>
#include <queue>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

// ---------------------------------------------------------------------------
// InferenceRequest
// ---------------------------------------------------------------------------

struct InferenceRequest {
    int id;
    int priority;           // higher = more urgent
    int token_count;        // simulated input tokens
    double enqueue_time_ms; // monotonic time at enqueue

    bool operator<(const InferenceRequest& o) const {
        return priority < o.priority; // max-heap by priority
    }
};

// ---------------------------------------------------------------------------
// Scheduler
// ---------------------------------------------------------------------------

class InferenceScheduler {
public:
    InferenceScheduler(int num_workers, int batch_size)
        : num_workers_(num_workers),
          batch_size_(batch_size),
          shutdown_(false),
          total_processed_(0) {}

    void start() {
        start_time_ = now_ms();
        for (int i = 0; i < num_workers_; ++i) {
            workers_.emplace_back(&InferenceScheduler::worker_loop, this, i);
        }
    }

    void enqueue(InferenceRequest req) {
        req.enqueue_time_ms = now_ms();
        {
            std::lock_guard<std::mutex> lk(mu_);
            queue_.push(req);
        }
        cv_.notify_one();
    }

    void shutdown() {
        {
            std::lock_guard<std::mutex> lk(mu_);
            shutdown_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_) {
            if (t.joinable()) t.join();
        }
    }

    void print_stats() const {
        double elapsed = now_ms() - start_time_;
        double throughput = (total_processed_ > 0)
            ? total_processed_ / (elapsed / 1000.0)
            : 0;

        std::vector<double> sorted_lat(latencies_.begin(), latencies_.end());
        std::sort(sorted_lat.begin(), sorted_lat.end());

        auto pct = [&](double p) -> double {
            if (sorted_lat.empty()) return 0;
            size_t idx = static_cast<size_t>(p * sorted_lat.size());
            idx = std::min(idx, sorted_lat.size() - 1);
            return sorted_lat[idx];
        };

        std::cout << "\n=== Inference Scheduler Stats ===\n"
                  << "Workers:     " << num_workers_ << "\n"
                  << "Batch size:  " << batch_size_ << "\n"
                  << "Processed:   " << total_processed_.load() << "\n"
                  << "Elapsed:     " << std::fixed << std::setprecision(1)
                  << elapsed << " ms\n"
                  << "Throughput:  " << std::setprecision(1) << throughput
                  << " req/s\n"
                  << "Latency p50: " << std::setprecision(2) << pct(0.50)
                  << " ms\n"
                  << "Latency p95: " << pct(0.95) << " ms\n"
                  << "Latency p99: " << pct(0.99) << " ms\n"
                  << "=================================\n";
    }

private:
    void worker_loop(int worker_id) {
        std::vector<InferenceRequest> batch;
        batch.reserve(batch_size_);

        while (true) {
            batch.clear();
            {
                std::unique_lock<std::mutex> lk(mu_);
                cv_.wait(lk, [&] { return !queue_.empty() || shutdown_; });
                if (shutdown_ && queue_.empty()) break;

                // Pull up to batch_size requests
                while (!queue_.empty() && (int)batch.size() < batch_size_) {
                    batch.push_back(queue_.top());
                    queue_.pop();
                }
            }

            if (batch.empty()) continue;

            // Simulate inference (1-5 ms per token, batched)
            int total_tokens = 0;
            for (auto& r : batch) total_tokens += r.token_count;
            double sim_ms = total_tokens * 0.02; // 0.02 ms per token
            std::this_thread::sleep_for(
                std::chrono::microseconds(static_cast<int>(sim_ms * 1000)));

            // Record latencies
            double done_time = now_ms();
            {
                std::lock_guard<std::mutex> lk(lat_mu_);
                for (auto& r : batch) {
                    latencies_.push_back(done_time - r.enqueue_time_ms);
                }
            }

            total_processed_ += batch.size();
        }
    }

    static double now_ms() {
        auto tp = std::chrono::steady_clock::now();
        return std::chrono::duration<double, std::milli>(tp.time_since_epoch())
            .count();
    }

    int num_workers_;
    int batch_size_;
    std::atomic<bool> shutdown_;
    std::atomic<int> total_processed_;
    double start_time_ = 0;

    std::mutex mu_;
    std::condition_variable cv_;
    std::priority_queue<InferenceRequest> queue_;

    std::mutex lat_mu_;
    std::deque<double> latencies_;

    std::vector<std::thread> workers_;
};

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

int main(int argc, char* argv[]) {
    int num_workers = 4;
    int batch_size = 8;
    int num_requests = 200;

    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg == "--workers" && i + 1 < argc) num_workers = std::atoi(argv[++i]);
        else if (arg == "--batch" && i + 1 < argc) batch_size = std::atoi(argv[++i]);
        else if (arg == "--requests" && i + 1 < argc) num_requests = std::atoi(argv[++i]);
    }

    std::cout << "Starting InferenceScheduler: workers=" << num_workers
              << " batch=" << batch_size << " requests=" << num_requests << "\n";

    InferenceScheduler scheduler(num_workers, batch_size);
    scheduler.start();

    // Enqueue requests with random priorities and token counts
    std::mt19937 rng(42);
    std::uniform_int_distribution<int> prio_dist(1, 10);
    std::uniform_int_distribution<int> tok_dist(50, 500);

    for (int i = 0; i < num_requests; ++i) {
        scheduler.enqueue({i, prio_dist(rng), tok_dist(rng), 0});
        // Slight stagger to simulate arrival
        std::this_thread::sleep_for(std::chrono::microseconds(200));
    }

    // Wait for processing
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    scheduler.shutdown();
    scheduler.print_stats();

    return 0;
}
