# Automatic local file restoration

Claude writes session tokens through its ordinary `Write` tool. After that tool
succeeds, Privacy Guard restores approved personal values in the same local file.
The selected destination is preserved; no separate export command or single
export directory is needed for this operation.

## Supported operation

- Native Windows, successful `PostToolUse` for `Write` only.
- UTF-8 TXT, Markdown (`.md` or `.markdown`) and comma-separated CSV files.
- An absolute path on a fixed local drive, with existing plain directory ancestry.
- One regular file, with no reparse point or additional hard link.
- At most 2 MiB for both the masked and restored file.

Other formats and operations keep tokens. This includes JSON, shell writes,
`Edit`, remote/MCP operations and the chat display. It is a deliberately bounded
first implementation, not coverage for every output channel. Relative, network,
device, alternate-stream and traversal paths do not restore. Paths are not
detokenized. A fixed local drive can still be cloud-synchronized.

External placeholders such as `PERSON_001` and `[EMAIL_001]` are retained literally
on reads, including when an older session had learned them as names. They need no
Privacy Guard restoration. Adjacent real personal values still receive this
session's tokens; this does not extend automatic restoration to Python or other
source-code files.

### Editing a restored document

For protected TXT, Markdown and CSV reads, the hook gives Claude generic guidance
to read the complete document and use `Write` for changes spanning placeholders.
The same guidance accompanies a structured `file_unchanged` Read result without
inventing a document body. Plain reads without placeholders need no guidance.

The PreToolUse `Edit` check also refuses placeholder-based edits when called, but
Claude Code can reject an exact-string mismatch before invoking that hook. This
was observed in the VS Code 2.1.289 trial and is also
[reported in Anthropic's tracker](https://github.com/anthropics/claude-code/issues/93311).
Read-time guidance reaches Claude before that validation; it is a workflow hint,
not a guarantee that the model follows it. Exact-string Edit can otherwise search
for tokens absent from the restored file, or insert tokens without restoration.
The hook does not recover original values into Edit arguments or modify a file
before normal permission checks. It neither runs nor approves the suggested
Write; Claude must choose it and the normal permission flow applies.

An Edit that only changes a plain amount, status or heading proceeds unchanged.
This rule does not implement automatic restoration for Edit, MultiEdit, shell
writes or other formats. It recognizes the current token/redaction syntax only;
it is workflow guidance rather than comprehensive write enforcement. Rewriting
a complete file requires a complete read; do not turn a truncated read into a
full-file Write. Limits and file checks described below still apply to Write.

Only body cells of CSV files are restored; headers retain tokens. CSV values are
quoted as needed and use CRLF output. Obvious spreadsheet expressions and malformed
CSV are rejected. This is not a complete spreadsheet-security validator. Plain
text preserves the file's existing UTF-8 BOM and line endings when replacing tokens.

## Ordering and cycle

Normal tool permissions apply to the masked Write. Privacy Guard does not create
or restore a file in `PreToolUse`, return original values in `updatedInput`, or
approve a tool on the user's behalf. It acts on the completed successful Write.
This ordering follows the [PostToolUse contract](https://code.claude.com/docs/en/hooks#posttooluse).

The hook pins each directory from the volume root downward, opens the written
file exclusively, and checks that its UTF-8 text still matches the tool's masked
content. LF and CRLF are treated as equivalent for this check; a UTF-8 BOM is
accepted. Matching contents do not prove the identity of the object originally
written if another process replaced it with identical bytes before the hook opened it.

Restoration reads only bound personal records from the same session. Unknown,
relabelled and legacy unbound tokens stay masked. Secrets stay redacted. No
original-value temporary file is created. The file is updated and truncated through
the same native handle, which prevents path changes from redirecting that write.
Link count is checked again after replacement. Windows sharing flags do not
prevent every hard-link creation; a detected alias makes the operation fail and
attempt rollback before exclusive access ends. Another process with the user's
privileges can still add a link after the last check or after the handle closes.

Tool results continue through protection. The additional feedback contains only
a generic restoration status. A native user-facing `systemMessage` also reports
successful restoration or an eligible restoration failure. Actual protection
changes receive a separate native notice with category occurrence counts and the
document basename when known; clean and already-tokenized reads do not claim a
new pseudonymization. These summaries also enter the local `protection.jsonl`
journal. Extracted body values, full paths and token identifiers are omitted.
A later supported read of the restored file goes
through normal detection and pseudonymization again. The file has no persistent
exemption from protection; current detector quality and input coverage still limit
what gets pseudonymized. Direct human prompts remain outside the agreed scope.

## Failures and evidence

If the file changed, is locked, linked, oversized, or its mapping/CSV is invalid,
the hook leaves it untouched and reports restoration failure when an eligible
attempt fails. Unsupported operations pass through with their tokens.
If replacement raises a handled error, the hook attempts to restore the original
masked bytes while retaining the exclusive handle.

Rollback can fail on storage/driver errors. A killed process or power failure can
leave partially restored bytes. This is not a transactional or secure-deletion
mechanism. Once the handle closes, permitted processes can read the file; the
agent and user share filesystem privileges. Earlier tool telemetry may capture
the tool's original result before the post hook runs.

Local tests exercise native handles, temporary DPAPI vaults and a launcher deployed
to a temporary home. They do not observe the actual request delivered to a live
model or establish fail-closed behavior for every tool schema or timeout. Updating
the user's installed hook remains a separate deployment step. Compatible updates
preserve session vaults; unknown or incompatible formats stop installation without
deleting them. Explicit uninstall still clears the vaults.
