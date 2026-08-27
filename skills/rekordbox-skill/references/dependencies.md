# Dependencies

Run a read-only preflight before installing anything:

```powershell
.\scripts\dependency_preflight.ps1
```

1. Identify the installed Rekordbox version and resolve `%APPDATA%\Pioneer\rekordbox\master.db` without opening it for write.
2. Use the backend bundled with this skill through its project-local locked environment.
3. Check for `uv`, a supported Python runtime, the pinned `pyrekordbox` and SQLCipher stack, and any Rekordbox processes or SQLite sidecars.
4. Report missing components and whether read-only inspection can proceed without them.

When dependencies are missing, offer a scoped installation. After approval, use the maintained lockfile and project-local environment:

```powershell
.\scripts\dependency_preflight.ps1 -Install
```

This default setup has no djay dependency. Do not install packages globally, upgrade Rekordbox, or replace the pinned pyrekordbox version as part of dependency setup. Follow the workspace supply-chain review rule before executing newly fetched third-party code. Verify database open/read-only inspection after installation before considering any mutation.

Use only the locked SQLCipher wheel resolved by this repository. Never invoke pyrekordbox's optional `install-sqlcipher` command, which performs its own source checkout and build outside this lock. Keep pyrekordbox logging above `DEBUG` during Collection access because upstream debug output can expose decoded database-key material.
