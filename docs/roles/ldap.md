# Role: ldap

The user directory of the homelab: [lldap](https://github.com/lldap/lldap), a
lightweight LDAP server with a web UI, as a rootless Podman container. Tag:
`ldap`. Source: `roles/ldap/`. Depends on [bashrc_loader](bashrc_loader.md) and
[mkcert](mkcert.md). The OpenID Connect side is the [authelia](authelia.md)
role; why the two exist and how apps use them is in
[identity for your apps](../features/identity-oidc-for-apps.md).

Why lldap and not a full OpenLDAP: it is one small binary with SQLite, it
manages users and groups through a UI, and that is what apps need (bind,
search, group membership). It does not support custom schemas or arbitrary LDAP
writes.

## What it does

1. Installs podman and openssl; creates the `ldap` service user with lingering,
   like the `forgejo` and `monitoring` roles.
2. Creates `/home/ldap/identity/` (`secrets/` 0700, `tls/`).
3. **Certificate.** With `identity_tls_source: mkcert` (default) it issues one
   certificate for `ldap.<domain>`, `auth.<domain>`, `localhost` and
   `127.0.0.1` from `desktop_user`'s mkcert CA, and renews it when the names
   change or 30 days remain. Run `mkcert -install` once as your user first
   (it makes your browser trust the CA); the role stops with that message if
   the CA is missing. With `files` you supply your own certificate and key.
4. **Secrets.** Generated once (never overwritten) as files in `secrets/` (0600)
   and as Podman secrets: the lldap JWT secret, the admin password and the bind
   password.
5. Deploys the `identity` network and the `lldap` Quadlet unit and starts it.
6. **Provisioning**, through lldap's HTTP API on loopback: creates the groups in
   `identity_ldap_groups` and the read-only bind account `authelia` (password
   from `secrets/`, group `lldap_strict_readonly`). It only creates what is
   missing.
7. On this machine: adds the two names to `/etc/hosts`; adds firewalld reject
   rules so the LDAPS and Authelia ports are not reachable from the LAN
   (pods are unaffected); writes the k3s DNS override and the
   `identity-*` shell helpers.

## Using it

- Web UI: `http://localhost:17170`, user `admin`. The password:
  `sudo cat /home/ldap/identity/secrets/identity_lldap_admin_password`.
  Create people and groups there.
- Apps use LDAPS: `ldaps://ldap.lab.internal:6360`, base DN `dc=lab,dc=internal`.
  Users live under `ou=people`, groups under `ou=groups`. Give an app that needs
  to search its own bind account (add it in the UI to `lldap_strict_readonly`).
- `identity-info` prints these values.
- `homelab up|down|status identity` ([homelab command](../features/homelab-command.md))
  starts and stops it together with Authelia.

## Ports

| Port | Published on | Purpose |
|---|---|---|
| 6360 | `identity_bind_address` (blocked from the LAN by default) | LDAPS, for apps |
| 17170 | `127.0.0.1` | web UI |
| 3890 | not published | plain LDAP, only on the internal `identity` network for Authelia |

See [networking](../features/networking.md).

## Settings (`roles/ldap/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `identity_user` | `ldap` | service user for lldap and Authelia |
| `identity_domain` | `lab.internal` | DNS domain; names are `auth.<domain>` and `ldap.<domain>`. Authelia must accept it; if it refuses `lab.internal`, use a subdomain of a domain you own |
| `identity_base_dn` | derived (`dc=lab,dc=internal`) | LDAP base DN |
| `identity_bind_address` | `0.0.0.0` | where LDAPS and Authelia are published |
| `identity_host_address` | this host's default IPv4 | the address pods and other machines use; goes into the k3s DNS override |
| `identity_hosts_address` / `identity_manage_hosts` | `127.0.0.1` / `true` | what `/etc/hosts` here maps the names to |
| `identity_ldaps_port` / `identity_authelia_port` / `ldap_web_port` | `6360` / `9443` / `17170` | |
| `identity_lan_access` / `identity_manage_firewalld` | `false` / `true` | firewalld rules |
| `identity_tls_source` | `mkcert` | or `files` (`identity_tls_cert_src`, `_key_src`, `_ca_src`); `identity_tls_extra_names` adds names |
| `ldap_image` | `lldap/lldap:2026-09-22-alpine-rootless` | pinned; lldap migrates its database forward |
| `ldap_admin_email` | `admin@<domain>` | |
| `identity_ldap_groups` | `[]` | groups to create |
| `identity_bind_user` | `authelia` | read-only account Authelia binds with |

## Files and commands

| What | Where |
|---|---|
| secrets (0600) | `/home/ldap/identity/secrets/` |
| certificate, key, CA (public copy) | `/home/ldap/identity/tls/` |
| CA certificate and k3s DNS manifest for your user | `~/.config/homelab/identity/` |
| shell helpers | `~/.bashrc.d/identity.sh`: `identity-info`, `identity-oidc-secret`, `identity-k3s-link` |
| backup / restore | [identity backup](../features/identity-backup.md) |

## Not verified

Written from the upstream documentation and tested only by rendering the
templates; there is no Podman in the build environment. In particular the
rootless lldap image's first start, the `lldap_set_password` call, and the
firewalld rules need a first real run. If provisioning fails, the admin
password and `journalctl --user -u lldap` (as the `ldap` user) say why.
