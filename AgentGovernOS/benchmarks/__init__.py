"""AgentGovern OS — Performance Benchmark Suite.

benchmarks measure the latency of the critical hot-path:
    /governance/evaluate  (the endpoint every SDK connector calls)
    Policy engine (pure-Python rule evaluation loop)

Run:
    pytest benchmarks/ --benchmark-only
    pytest benchmarks/ --benchmark-only --benchmark-json=benchmarks/results.json
"""
