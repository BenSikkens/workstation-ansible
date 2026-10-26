# Role: forgejo

Self-hosted git (Forgejo) plus an Actions runner and a CI scanner image. Tag:
`forgejo`. Source: `roles/forgejo/`.

Runs as a **rootless** Podman container under a dedicated `git` user, managed as
a systemd **user** service through a
[Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
unit at `~git/.config/containers/systemd/forgejo.container`. Systemd lingering
is enabled for `git`, so the services survive reboots without anyone logging in
as that user.

## What it does, in order

1. [Backs up](../features/forgejo-backup.md) an existing install (no-op on a
   fresh machine; skipped with `forgejo_backup_enabled: false`).
2. Installs `podman`, `slirp4netns`, `passt`, `fuse-overlayfs`.
3. Creates the `git` user, enables lingering, makes sure its systemd user
   manager runs, and enables its rootless Podman socket (the runner needs it).
4. Creates the data and runner data directories and the Quadlet directory.
5. Deploys the shared Podman network unit (`forgejo.network`) and the Forgejo
   container unit; opens the HTTP and SSH ports in firewalld
   (`forgejo_http_port`, `forgejo_ssh_port`).
6. Enables and starts Forgejo.
7. Builds the [CI scanner image](../features/ci-scanners.md) if any scanner is
   enabled.
8. Sets up the [Actions runner](../features/forgejo-runner.md).
9. Records the install outcome for the backup (`pending` becomes `success` once
   `/api/healthz` answers and both services are active).

## After the run

- Web UI and first-run wizard: `http://localhost:3000`
- Clone over SSH: `git clone ssh://git@localhost:2222/<owner>/<repo>.git`
  (add an entry for the non-standard port to `~/.ssh/config`)
- Check the service:
  ```bash
  sudo machinectl shell git@
  systemctl --user status forgejo.service
  podman logs forgejo
  ```

This role gets the container running and persistent. It does not configure
Forgejo itself (admin account, `APP_URL`, ...). That is done once in the
first-run wizard, or later by editing
`/home/git/forgejo-data/data/gitea/conf/app.ini`, which this playbook never
writes.

## Settings (`roles/forgejo/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_user` | `git` | system user the containers run as |
| `forgejo_image` | `codeberg.org/forgejo/forgejo:16` | pinned to a major version, not `latest`. **Never lower it on an existing install:** Forgejo refuses a database written by a newer release. Raising it migrates the database forward, which cannot be undone |
| `forgejo_data_dir` | `/home/git/forgejo-data` | persistent data |
| `forgejo_http_port` | `3000` | web UI |
| `forgejo_ssh_port` | `2222` | git over ssh. Not 22: that is the host's sshd, and rootless containers cannot bind ports below 1024 on the host side |
| `forgejo_network_name` | `forgejo` | the Podman network shared with the runner and the Pushgateway |

Runner, scanner and backup variables are on their own pages:
[runner](../features/forgejo-runner.md), [scanners](../features/ci-scanners.md),
[backup](../features/forgejo-backup.md).

## Network exposure

Forgejo is published on **all interfaces** (LAN reachable), unlike the
monitoring stack. See [networking](../features/networking.md) for how to make it
local-only.

## Related

- [scan results on the dashboard](../features/scan-report.md)
- `homelab up|down forgejo` ([homelab command](../features/homelab-command.md))
- [overwrite policy](../features/overwrite-policy.md)
