# AgentStudio — Run State Machine

Every agent execution run in AgentOS follows this strict state machine.

```
                    ┌──────────────┐
                    │    QUEUED    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  VALIDATING  │
                    └──────┬───────┘
                   /       │        \
         (invalid)/        │         \(error)
                 ▼         │          ▼
            ┌─────────┐    │     ┌─────────┐
            │ FAILED  │    │     │ FAILED  │
            └─────────┘    │     └─────────┘
                           ▼
                    ┌──────────────┐
                    │ POLICY_CHECK │
                    └──────┬───────┘
                 /         │         \
           (deny)/     (allow)        \(escalate)
                ▼          │           ▼
          ┌─────────┐      │      ┌───────────┐
          │ BLOCKED │      │      │ ESCALATED │
          └─────────┘      │      └─────┬─────┘
                           │        /       \
                           │ (approve)    (reject)
                           │    /           \
                           ▼   ▼             ▼
                    ┌──────────────┐    ┌───────────┐
                    │  SCHEDULING  │    │ CANCELLED │
                    └──────┬───────┘    └───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │ SANDBOX_PROVISIONING  │
               └───────────┬───────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   RUNNING    │
                    └──────┬───────┘
                /          │          \
         (done)/        (error)        \(user cancel)
              ▼            ▼            ▼
       ┌───────────┐  ┌─────────┐  ┌───────────┐
       │ COMPLETED │  │ FAILED  │  │ CANCELLED │
       └───────────┘  └─────────┘  └───────────┘
```

## State Definitions

1. **QUEUED**: Run created, received idempotency key, waiting for validation worker.
2. **VALIDATING**: Checking JSON Schema v1 compliance, verifying tool definitions exist, validating manifest hash.
3. **POLICY_CHECK**: Evaluating server-authoritative policy against GovernOS SENTINEL.
   - Output: ALLOW, DENY, or ESCALATE.
4. **BLOCKED**: Hard policy failure. Run terminates immediately. ANCESTOR event recorded.
5. **ESCALATED**: Paused awaiting human-in-the-loop approval via GovernOS ECLIPSE.
6. **SCHEDULING**: Policy passed. Worker assigned from Redis execution pool.
7. **SANDBOX_PROVISIONING**: Container/gVisor microVM booted, short-lived secrets injected.
8. **RUNNING**: Execution active. Step telemetry emitted over WebSockets/SSE.
9. **COMPLETED**: All steps completed within budget and time limits.
10. **FAILED**: Runtime exception, tool timeout, unhandled error.
11. **CANCELLED**: Explicit user cancellation or timeout.
