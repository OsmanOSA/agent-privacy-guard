# Local CSV export

The agent works with tokens and writes a masked CSV. An explicit local command
restores personal values into a new CSV in the selected export directory.
Claude Code hooks do not return original values in tool arguments.
Successful supported Write operations can also restore in place; see
[automatic local file restoration](automatic-restoration.md). This manual export
command retains its separate directory policy.

## Configuration

Keep `export-policy.json` in the guard home, normally `~/.privacy-guard`:

```json
{
  "version": 1,
  "root": "C:\\Users\\dev\\PrivacyGuardExports"
}
```

Replace the example with an existing directory chosen by the user. A missing
file or `null` root disables export. Invalid configuration fails the export
command; it does not interfere with ordinary agent tools. This source change
does not create directories, edit live settings or install the hook.

The root must be on a fixed local Windows drive, without reparse points in its
ancestry. UNC paths, device paths, mapped network drives and stream names are
excluded. A local directory can still be cloud-synchronized; choose the root
according to the intended disclosure policy.

## Export during an active session

Ask the agent for a comma-separated CSV containing its session tokens. From a
separate terminal, while that session's vault still exists, run:

```powershell
python -m privacy_guard export --source masked.csv --session SESSION_ID --filename clients.csv
```

The session identifier is the `session_id` supplied by Claude Code's hook
payload. It is also the name of the corresponding directory under the guard's
`vault` directory. No session discovery UI is included in this step. Use
`--guard-home PATH` if the vault and policy are under a custom guard directory.
Session end or uninstall can remove the mappings, so perform this
explicit export before ending the session. Unknown tokens stay masked.

The source is read as UTF-8, accepting a BOM; it is never modified. The output
must be a plain filename for a new `.csv` directly in the configured root.
Only body cells are restored. Headers and secrets stay masked; CSV quoting
preserves commas, quotes and newlines in originals. Output uses UTF-8 and CRLF.
The CSV checks reject obvious spreadsheet expressions, not every possible
spreadsheet hazard. This command restores mappings; it is not a general
sanitizer for arbitrary raw input.

The command prints only a success/failure receipt. It does not print personal
values, the restored CSV or an error traceback. Run it outside the agent; no
automatic export, MCP registration or permission bypass is introduced.

## Destination control

The Windows writer opens each directory from the volume root downward, rejects
reparse points on the opened handles, and holds them without delete sharing
until the write finishes. A plain directory and its ancestors therefore remain
pinned during the operation. The final file is created with `CREATE_NEW`, never
with a replacement disposition. Concurrent creation fails instead of overwriting.
These choices follow [Microsoft's CreateFileW contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

The new file has exclusive sharing while its UTF-8 bytes are written and flushed.
A handled write failure requests deletion on that same handle, following
[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle).
No restored-value temporary file is created outside the authorized directory.

## Remaining limits

This is a native Windows writer. It has no fallback writer for other platforms.
Storage/driver failures can prevent cleanup, and abrupt process termination or
power loss can leave an incomplete output. This step does not provide a
transactional, crash-safe publication guarantee or secure deletion.

After the export closes, other permitted processes can read or move the file.
The agent shares the user's filesystem privileges; running the command outside
the agent is an explicit workflow choice, not an operating-system access barrier.
Hook failure behavior and real model requests still need separate observation.

Legacy unbound mappings are ignored by the current restorer; they are not
migrated or deleted. A fresh protected read can issue a bound mapping for the
same value. Compatible reinstallations now preserve session vaults. An unknown
or incompatible format stops installation without deleting the mappings.
Deployment remains an explicit separate operation.
