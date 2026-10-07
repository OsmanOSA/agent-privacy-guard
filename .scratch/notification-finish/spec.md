# Windows notification completion

Implement quiet-state suppression with a conservative native fallback, a hidden
renderer preparation handshake so foreground is checked after WPF startup,
monitor-aware placement, and a verified return-to-host button. Never execute
commands or infer an exact chat tab from a window handle. Keep modules small.

Use only counts/basenames already allowed in notifications. Quiet-state discovery
is read-only; failure must not affect protection. WNF quiet-profile discovery is
an undocumented Windows compatibility adapter, not a public API guarantee.
Unknown or malformed state routes to the shell-managed native renderer.

Validate suppression during startup, focus changes, process reuse, unknown quiet
state, monitor geometry and cleanup with synthetic data. Run the baseline suite
before upgrading the global installation and enabling background card delivery.
Preserve existing vaults/settings/model configuration and record deployment hashes.
Exact editor tab navigation and non-Windows hosts remain separate integrations.
