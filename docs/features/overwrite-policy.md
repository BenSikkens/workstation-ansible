# Overwrite policy: what the playbook rewrites

Most tasks (`dnf`, `community.general.flatpak`) only install packages. They
never touch your configuration or data, so there is nothing to protect. The
places that *do* write a file outright are listed here, with what is done about
each. Preview them with `ansible-playbook site.yml --check --diff`
([running the playbook](running-the-playbook.md)).

| What is written | Behaviour |
|---|---|
| Existing Forgejo data | Archived before any change; see [Forgejo backup](forgejo-backup.md). |
| Forgejo / runner Quadlet units (`roles/forgejo/templates/*.j2`) | Re-rendered and reapplied on every run, by design, so changing a default (a port, an image tag) propagates. All use `backup: true`: if the content changes, a timestamped copy of the previous version is saved next to it first. |
| Forgejo runner `config.yml` | Re-rendered every run (so label and scanner toggles take effect), with `backup: true`. The runner's identity is **not** in this file: its UUID and secret live in `.runner-uuid` / `.runner-secret` (mode 0600) beside it, created once at registration and never overwritten (`force: false`), so re-rendering cannot re-register the runner. Because `config.yml` holds the secret, tasks touching it use `diff: false` and it never appears in `--check --diff` output. |
| CI image `Containerfile` | Rendered with `backup: true`; the image is rebuilt only when it changed or is missing. |
| `~/.bashrc` | Only touched if it does not already load `~/.bashrc.d/` (Fedora's default does), and then via a marked block with a backup. The `homelab` command and k3s helpers are separate drop-ins in `~/.bashrc.d/`, written **without** backups because everything in that directory is sourced. |
| Forgejo `app.ini`, vault and repository data | Never templated or written by this playbook. Forgejo manages them itself. |
| `/etc/sudoers.d/homelab` | Generated and checked with `visudo -cf` before it is installed. |
| k3s kubeconfig copy (`~/.kube/k3s.yaml`) | Overwritten from `/etc/rancher/k3s/k3s.yaml` on each run (and by `homelab up k3s`); shown with `diff: false` because it holds cluster credentials. |

## Hand edits

If you edit a deployed Quadlet unit directly on the machine, the next playbook
run puts it back to the template's version (a backup is kept). The repo is the
source of truth. To make a change stick, change the `.j2` template or the
role's `defaults/main.yml` (or `group_vars/all.yml`) instead. For an example
see "Making a change permanent" in [networking](networking.md).
