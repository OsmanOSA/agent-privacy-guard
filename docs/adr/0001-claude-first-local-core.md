---
status: accepted
date: 2026-10-05
---

# Start with Claude Code and keep the privacy core local

The founder deliberately chose Claude Code as the first agent so that interception, pseudonymization and restoration can be validated on one integration before expanding to other vendors. Detection and session mappings remain local, with agent-specific protocol handling outside the core; today's native vault implementation uses Windows DPAPI.

Supporting every agent immediately would spread compatibility and security work across several changing protocols. Starting with one adapter trades breadth for a clearer test surface. New adapters must demonstrate their own covered paths; the first adapter is not evidence of universal protection.
