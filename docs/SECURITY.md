# Security Policy

## Filesystem Isolation
DebugGenie uses a strict workspace isolation model to prevent unauthorized access to sensitive files.

### Workspace Root
All file operations are restricted to the configured workspace directory.
- Default: `./workspace`
- Configurable via `DEBUGGENIE_WORKSPACE` environment variable.

### Path Validation
- **Path Traversal**: All paths are resolved and checked to ensure they remain within the workspace root. `../` attempts escaping the workspace are blocked.
- **Absolute Paths**: Absolute paths are blocked unless they resolve to within the workspace.
- **Symlinks**: Symlinks are followed during resolution, but the final target must be within the workspace.

### Blacklisted Files
The following patterns are explicitly denied access, even if they exist within the workspace:
- `.env`, `.env.*` (Environment secrets)
- `*.pem`, `*.key`, `id_rsa*` (Private keys)
- `.git/*` (Version control history)
- `.ssh/*`, `.aws/*`, `.config/*` (System credentials)
- `secrets/*`, `credentials/*` (Explicit secret directories)

## Rate Limiting
To prevent abuse, file access is rate-limited:
- **Limit**: 100 requests per minute per client.
- **Scope**: Applied to `read_file`, `list_files`, `get_file_context`, and `search_in_files`.

## Audit Logging
All file access attempts are logged with the `SECURITY_AUDIT` tag.
Format:
```
SECURITY_AUDIT | {operation} | {file_path} | client={client_id} | allowed={bool} | {reason}
```

## Incident Response
If a security violation is detected (e.g., repeated access denied logs):
1. Identify the `client_id` from logs.
2. Revoke access if applicable.
3. Rotate any potentially exposed credentials if a bypass is suspected.
4. Report the incident to the security team.
