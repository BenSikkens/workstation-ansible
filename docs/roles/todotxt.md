# Role: todotxt

`todo.txt-cli` and the **Todo.txt** GNOME Shell extension. Tag: `todotxt`.
Source: `roles/todotxt/`.

This role acts on **your own desktop login** (`desktop_user`), not on a
dedicated service user, because GNOME Shell extensions are per user.
`desktop_user` is set in `group_vars/all.yml` and defaults to whoever runs
`ansible-playbook`.

## todo.txt-cli

No Fedora package, so it comes from upstream's GitHub releases:

1. With `todotxt_cli_version: "latest"` the current release is resolved via the
   GitHub API at run time; otherwise the given tag is used.
2. The tarball is extracted to `/opt/todo.txt-cli` (skipped once `todo.sh`
   exists).
3. `todo.sh` is made executable and symlinked as `/usr/local/bin/todo.sh` and
   `/usr/local/bin/todo`.

## The GNOME Shell extension

1. Detects the GNOME Shell major version.
2. Asks extensions.gnome.org's `extension-info` API for extension id `570`, which
   returns the UUID and the right build for that Shell version, so nothing is
   hardcoded to go stale.
3. Downloads it into `~/.local/share/gnome-shell/extensions/<uuid>/`, **once**.
   If GNOME's own updater later replaces it, this role does not overwrite that.
4. Enables it with `gnome-extensions enable`.

**Run the playbook from a terminal inside your active GNOME session.** Enabling
the extension writes to your dconf database over your session's D-Bus; from a
plain TTY or a headless SSH session the last task fails.

After the first run, log out and in (or restart GNOME Shell with Alt+F2, `r`,
Enter on X11 only) before the extension shows up.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `todotxt_cli_version` | `"latest"` | or an exact tag such as `"v2.12.0"` to stop it moving |
| `todotxt_cli_install_dir` | `/opt/todo.txt-cli` | |
| `todotxt_gnome_extension_pk` | `570` | extension id on extensions.gnome.org |
