# Identity backup and restore (`identity-backup.yml`)

What to protect: the lldap database (users, groups), Authelia's database
(sessions, consents), the generated secrets, and the TLS files.

```bash
ansible-playbook identity-backup.yml --ask-become-pass
ansible-playbook identity-backup.yml --ask-become-pass -e identity_restore_from=/var/backups/identity/identity-<timestamp>.tar
```

- **Backup** stops lldap and Authelia (so SQLite is copied quietly), exports the
  volumes `lldap-data` and `authelia-data` with `podman volume export`, adds the
  `identity/` directory (secrets and TLS) and writes one archive to
  `/var/backups/identity/` (root-only, mode 0600), then starts the services
  again.
- **Restore** stops them, unpacks the archive, puts the files and volumes back,
  re-creates the Podman secrets from the restored secret files (the roles only
  create a secret that is missing, so this step matters after a fresh install),
  and starts the services.

The archive contains private keys and password hashes. Keep it somewhere you
trust and encrypt it before it leaves this machine.

Not in the backup: container images (pulled again) and the monitoring data
(see [monitoring](../roles/monitoring.md)). Restores into an existing install
overwrite the current users and groups; nothing is kept as a `.failed` copy, so
make a fresh backup first if in doubt. Used when
[moving the stack](identity-moving.md).

Not tested on a real machine (`podman volume export/import` as the `ldap`
user in particular).
