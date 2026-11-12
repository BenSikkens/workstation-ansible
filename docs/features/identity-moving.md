# Moving the identity stack to a dedicated machine

The stack was built so that the move is a data move plus one address change.
Nothing in your apps refers to the old machine: they use
`auth.lab.internal:9443` and `ldap.lab.internal:6360`.

## What is machine-specific

| Thing | Where | On the new machine |
|---|---|---|
| Names → address | `/etc/hosts` here (`identity_hosts_address`) and the k3s DNS override (`identity_host_address`) | point both at the new host |
| TLS certificate | `/home/ldap/identity/tls/` | restored from the backup (same names, so still valid) |
| Users, groups, Authelia state | Podman volumes `lldap-data`, `authelia-data` | restored from the backup |
| Secrets | `/home/ldap/identity/secrets/` | restored from the backup |
| Open ports | firewalld | on a LAN host set `identity_lan_access: true` and restrict the source to the cluster nodes yourself |

## Steps

1. Back up: `ansible-playbook identity-backup.yml --ask-become-pass`
   ([identity backup](identity-backup.md)).
2. On the new machine, check out this repository and install the roles there
   (`ansible-playbook site.yml --tags authelia`; use an inventory that targets
   that host). This creates the user, units and fresh secrets.
3. Copy the archive over and restore:
   `ansible-playbook identity-backup.yml --ask-become-pass -e identity_restore_from=...`.
   Restore replaces the volumes, the secrets and the certificate files.
4. Point the names at the new host: in `group_vars` set
   `identity_host_address` to its address, and on this workstation set
   `identity_hosts_address` the same (or stop managing `/etc/hosts` and use your
   router's DNS). Re-run `--tags ldap` here, then `identity-k3s-link`.
5. Stop and disable the stack on the workstation
   (`homelab down identity`, then remove the units if you like).

## Limits

- `homelab` only looks at the machine it runs on. On the new server run it
  there, or manage the units over ssh yourself; a remote mode does not exist.
- The mkcert CA lives on your workstation. The restored certificate stays valid
  as long as the names do not change and until it expires; renewing it needs the
  CA, so either keep running the `ldap` role from the workstation or switch to
  `identity_tls_source: files` with certificates you issue elsewhere.
- Changing `identity_domain` or the Authelia port changes the OIDC issuer, which
  means updating every app and re-issuing the certificate.
