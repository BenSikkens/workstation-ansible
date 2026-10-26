# Forgejo backup, restore and cleanup

Playbook: `forgejo-backup.yml`. Tasks: `roles/forgejo/tasks/backup.yml` and
`backup_outcome.yml`. Role: [forgejo](../roles/forgejo.md).

## What happens during `site.yml`

If Forgejo data already exists, `site.yml` takes a backup **before the forgejo
role changes anything**:

1. It stops Forgejo and the runner, so the SQLite database and git repositories
   are copied quietly.
2. It archives the data dir, the runner data dir and the Quadlet units (numeric
   ownership kept, plus a SHA-256) into `/var/backups/forgejo/<timestamp>/`
   (root-only).
3. It records the backup in `/var/backups/forgejo/manifest.yml` with
   `status: pending`.
4. Once the role has verified that Forgejo answers on `/api/healthz` and both
   services are active, it flips the manifest to `status: success`.

On a fresh machine there is nothing to back up and no manifest is written.

## What you do afterwards

```bash
ansible-playbook forgejo-backup.yml --ask-become-pass
```

What it does depends on the recorded status:

| Recorded status | Meaning | `auto` does |
|---|---|---|
| `success` | install finished, Forgejo + runner healthy | **removes** the backup(s) |
| `pending` | install died before it was verified | **restores** the backup (asks you to type `yes`) |
| `restored` | a rollback already happened | removes the backup(s) |

Force a decision with `-e backup_action=restore` or `-e backup_action=remove`.
Skip the prompt (needed without a terminal) with `-e backup_confirmed=true`.

## Notes

- Restoring **never deletes** what it replaces: the broken directories are
  renamed to `<path>.failed-<timestamp>` next to the originals. Delete them
  yourself when done. The archive is checked against its recorded checksum
  before anything is moved; a mismatch aborts untouched.
- If a run fails and you re-run `site.yml` instead of restoring, the original
  backup is kept as the restore point (no new backup of the half-installed
  state) until a run finishes successfully.
- "Outcome" means the forgejo role. A later failure in another role (for
  example devpod) does not trigger a Forgejo rollback.
- The backup stops Forgejo for as long as the copy takes (seconds to a few
  minutes, depending on repository size) and needs free space for a copy of the
  data; an up-front check aborts before changing anything if there is not
  enough.
- **Not in the backup:** container images, the CI image, firewall rules, the
  `homelab` command, anything outside the three paths, and the
  [monitoring](../roles/monitoring.md) data. These are recreated by re-running
  the playbook (monitoring loses history only).

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_backup_enabled` | `true` (`group_vars/all.yml`) | turn the backup off with `false` |
| `forgejo_backup_dir` | `/var/backups/forgejo` | where archives go |
| `forgejo_backup_paths` | data dir, runner data dir, Quadlet dir | what is archived |
