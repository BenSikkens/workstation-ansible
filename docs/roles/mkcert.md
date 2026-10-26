# Role: mkcert

mkcert, for locally trusted development certificates. Tag: `mkcert`. Source:
`roles/mkcert/`.

Packaged in Fedora's repositories; the role is a single `dnf` install. It does
**not** run `mkcert -install` (that adds a root CA to your trust stores, which
is left as a deliberate step for you). RedHat family only. No settings.
