# Manifest reference

Create manifests locally and keep machine-specific manifests out of public repositories. Each item requires:

```json
{
  "items": [
    {
      "name": "Example privileged helper",
      "scope": "system",
      "label": "com.example.helper",
      "plist": "/Library/LaunchDaemons/com.example.helper.plist",
      "expected_program": "/Library/PrivilegedHelperTools/com.example.helper",
      "owner_app_absent": "/Applications/Example.app",
      "artifacts": [
        "/Library/LaunchDaemons/com.example.helper.plist",
        "/Library/PrivilegedHelperTools/com.example.helper"
      ]
    }
  ]
}
```

Fields:

- `name`: Human-readable audit label.
- `scope`: `user` for the invoking user's GUI domain or `system` for a system daemon.
- `label`: Exact value of the plist `Label` key.
- `plist`: Exact launchd plist path.
- `expected_program`: Exact `Program` value or first `ProgramArguments` value found in the plist.
- `owner_app_absent`: Expected application bundle under `/Applications` or the invoking user's `~/Applications` directory. The path must be absent.
- `artifacts`: Exact regular files permitted for backup and deletion. Include the plist.

The script accepts user artifacts only in `~/Library/LaunchAgents`. It accepts system artifacts only in `/Library/LaunchAgents`, `/Library/LaunchDaemons`, and `/Library/PrivilegedHelperTools`. It rejects symlinks, directories, duplicate paths, owner applications that still exist, and plist label/program mismatches.
