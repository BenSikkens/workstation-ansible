# Role: authelia

[Authelia](https://www.authelia.com) as the OpenID Connect (OIDC) provider for
your apps, with the [ldap](ldap.md) role's lldap as its user store. Tag:
`authelia`. Source: `roles/authelia/`. Depends on [ldap](ldap.md), so
`--tags authelia` installs both.

Apps do not handle passwords or LDAP binds themselves: they redirect users to
Authelia and receive signed tokens. How to wire an app up is in
[identity for your apps](../features/identity-oidc-for-apps.md).

## What it does

1. Generates its secrets once (session, storage encryption key, password-reset
   JWT secret, OIDC HMAC secret, RSA signing key) as 0600 files and Podman
   secrets (via the ldap role's `secret.yml`).
2. For each **confidential** client in `authelia_oidc_clients` it makes a random
   secret and its PBKDF2 digest with Authelia's own tool, once. The secret
   stays in `/home/ldap/identity/secrets/oidc-client-<id>.secret`; only the
   digest goes into the configuration.
3. Renders `/home/ldap/identity/authelia/configuration.yml`: TLS on the same
   certificate as LDAPS, LDAP backend `lldap` over the internal network, one
   session cookie for the domain, SQLite storage, and the OIDC clients. Without
   clients, OIDC is left out (Authelia refuses an OIDC section with no clients).
4. Deploys the `authelia` Quadlet unit on the `identity` network, restarts it
   when configuration, unit or certificate change, and waits for
   `/api/health`.

## Defining clients

In `group_vars/all.yml`, one entry per app, then `ansible-playbook site.yml --tags authelia --ask-become-pass`:

```yaml
authelia_oidc_clients:
  - id: myapp
    name: My App
    redirect_uris:
      - https://myapp.lab.internal/oauth2/callback
  - id: myapp-spa            # a browser app without a secret
    public: true
    redirect_uris: ["https://spa.lab.internal/callback"]
```

| Key | Default | Meaning |
|---|---|---|
| `id` | required | letters, digits and `. _ ~ -` |
| `name` | the id | shown on the consent screen |
| `redirect_uris` | required | exact URLs, case-sensitive |
| `public` | `false` | `true` = no secret (PKCE only) |
| `scopes` | `openid profile email groups` | add `offline_access` for refresh tokens |
| `policy` | `authelia_oidc_default_policy` (`one_factor`) | `two_factor` needs 2FA enrolled in Authelia |
| `require_pkce` | `true` | S256 |

Read a client's secret: `identity-oidc-secret myapp` (asks for your sudo
password).

## Ports

Authelia is published on `identity_bind_address:9443` over HTTPS and is blocked
from the LAN by default, like LDAPS. The issuer URL is
`https://auth.lab.internal:9443` (9443 rather than Authelia's usual 9091, which the Pushgateway uses; the name and port are part of the issuer, so
changing them means updating every app).

## Settings (`roles/authelia/defaults/main.yml`)

| Variable | Default |
|---|---|
| `authelia_image` | `docker.io/authelia/authelia:4.39` |
| `authelia_log_level` | `info` |
| `authelia_oidc_clients` | `[]` |
| `authelia_oidc_default_policy` | `one_factor` |
| `authelia_config_dir` | `/home/ldap/identity/authelia` |

Shared settings (domain, ports, user, certificate) are in [ldap](ldap.md).

## Notes

- Passwords are changed in the lldap UI. Authelia's own reset flow is disabled
  because its bind account is read-only.
- There is no forward-auth/reverse-proxy protection here (`access_control`
  denies everything); apps are protected by OIDC only.
- No e-mail is configured; Authelia's notifier writes to a file in its data
  volume.

## Not verified

The configuration follows Authelia's documentation for version 4.39 and was
only rendered and parsed here, not run. The first start may show a validation
error (e.g. about the cookie domain); `podman logs authelia` as the `ldap` user
shows it. `lab.internal` as the cookie domain is the most likely thing to be
rejected; change `identity_domain` if so.
