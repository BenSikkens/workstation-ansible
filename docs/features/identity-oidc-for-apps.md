# Identity for your apps (lldap + Authelia + k3s)

The pieces: [ldap](../roles/ldap.md) keeps users and groups,
[authelia](../roles/authelia.md) turns them into OpenID Connect logins, and your
apps in k3s only speak OIDC.

```
 browser ──► your app (k3s) ──redirect──► Authelia (https://auth.lab.internal:9443)
                │                              │ checks the password against
                └── verifies tokens ◄──────────┘ lldap (internal network)
```

Everything runs on the host in rootless Podman, outside the cluster, so it
survives `homelab down k3s` and can move to another machine
([moving it](identity-moving.md)).

## One-time setup

1. `mkcert -install` once as your user.
2. In `group_vars/all.yml` define your clients ([authelia](../roles/authelia.md))
   and optionally `identity_domain`.
3. `ansible-playbook site.yml --tags authelia --ask-become-pass`
4. Create people and groups in lldap: `http://localhost:17170` (user `admin`).
5. With k3s running (`homelab up k3s`): `identity-k3s-link my-namespace`.
   This makes `auth.lab.internal` and `ldap.lab.internal` resolve inside the
   cluster (a CoreDNS override pointing at this host) and creates the ConfigMap
   `homelab-ca` (the CA certificate) in the namespace.

Why DNS names and not a Kubernetes `Service`: the TLS certificate is issued for
`auth.lab.internal`, so apps can only verify it when they connect to that name.
When the stack moves, you change the address once; the apps keep their config.

## What an app needs

| Setting | Value |
|---|---|
| Issuer / discovery | `https://auth.lab.internal:9443` (`/.well-known/openid-configuration`) |
| Client id and secret | the entry in `authelia_oidc_clients`; `identity-oidc-secret <id>` prints the secret |
| Redirect URI | exactly as listed in `redirect_uris` |
| Scopes | `openid profile email groups`; the `groups` claim carries the lldap groups |
| PKCE | S256 (on by default) |
| Trust | mount ConfigMap `homelab-ca` and point the runtime at it |

A pod fragment (use your own names):

```yaml
spec:
  containers:
    - name: myapp
      env:
        - {name: OIDC_ISSUER, value: "https://auth.lab.internal:9443"}
        - {name: OIDC_CLIENT_ID, value: myapp}
        - name: OIDC_CLIENT_SECRET
          valueFrom: {secretKeyRef: {name: myapp-oidc, key: secret}}
        - {name: SSL_CERT_FILE, value: /etc/homelab-ca/ca.crt}        # Go, curl, Python's ssl
        # - {name: NODE_EXTRA_CA_CERTS, value: /etc/homelab-ca/ca.crt} # Node
      volumeMounts:
        - {name: homelab-ca, mountPath: /etc/homelab-ca, readOnly: true}
  volumes:
    - name: homelab-ca
      configMap: {name: homelab-ca}
```

Create the Kubernetes secret from the client secret without putting it in a file
you keep: `kubectl -n my-namespace create secret generic myapp-oidc --from-literal=secret="$(identity-oidc-secret myapp)"`.

`SSL_CERT_FILE` replaces the system trust store for that process (Python
`requests` reads `REQUESTS_CA_BUNDLE` instead), which is fine for talking to
Authelia but breaks other HTTPS calls; for those, bundle the CA
with the system CAs in your image instead.

## Using plain LDAP instead

Apps that cannot do OIDC can bind to `ldaps://ldap.lab.internal:6360` (base DN
`dc=lab,dc=internal`) with a read-only account created in the lldap UI
(group `lldap_strict_readonly`). Prefer OIDC for everything you write yourself.

## Adding Forgejo and Grafana later

Both support OIDC and LDAP. They run in rootless Podman under other users, so
two things differ from k3s apps and are not set up yet: the containers must
resolve `auth.lab.internal` to the host (`AddHost=` in their Quadlet; a
`127.0.0.1` entry in the host's `/etc/hosts` does not reach from inside a
container) and trust the CA. Not tested.

## Troubleshooting

| Symptom | Look at |
|---|---|
| `homelab status identity` shows stopped | `homelab up identity`; then `sudo -u ldap env XDG_RUNTIME_DIR=/run/user/$(id -u ldap) podman logs authelia` |
| Authelia rejects its configuration | the same log; the cookie `domain` rules are strict ([authelia](../roles/authelia.md)) |
| Browser warns about the certificate | `mkcert -install` was not run as your user, or the name is not in `/etc/hosts` |
| App: "x509: certificate signed by unknown authority" | the CA ConfigMap is not mounted or the runtime does not read `SSL_CERT_FILE` |
| App: cannot resolve `auth.lab.internal` | run `identity-k3s-link`; CoreDNS needs a restart to load the override (the helper does it) |
| App: connection refused / timeout | k3s pods reach the host via `identity_host_address`; check `ss -ltn \| grep -E '6360\|9443'` and firewalld ([networking](networking.md)) |
