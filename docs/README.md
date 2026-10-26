# Documentation

Every role and every feature of this repository has its own page. Start with
[running the playbook](features/running-the-playbook.md) if you are new here.

## Roles (one per piece of software)

In the order they run in `site.yml`.

| Role | Software | Install method | Page |
|---|---|---|---|
| `flatpak_setup` | Flatpak + Flathub remote (base for the Flatpak apps) | dnf | [flatpak_setup](roles/flatpak_setup.md) |
| `podman_desktop` | Podman Desktop | Flatpak | [podman_desktop](roles/podman_desktop.md) |
| `vim` | Vim, set as the default editor | dnf; swaps out `nano-default-editor` | [vim](roles/vim.md) |
| `vscodium` | VSCodium | dnf (official RPM repo) | [vscodium](roles/vscodium.md) |
| `keepassxc` | KeePassXC | dnf | [keepassxc](roles/keepassxc.md) |
| `mkcert` | mkcert | dnf | [mkcert](roles/mkcert.md) |
| `forgejo` | Forgejo git server, Actions runner, scanner CI image | rootless Podman (Quadlet) under user `git` | [forgejo](roles/forgejo.md) |
| `monitoring` | Grafana, Prometheus, Loki, Alloy, exporters, Pushgateway | rootless Podman (Quadlet) under user `monitoring`; Alloy from RPM | [monitoring](roles/monitoring.md) |
| `k3s` | single-node Kubernetes next to Podman | official installer, pinned | [k3s](roles/k3s.md) |
| `obsidian` | Obsidian | Flatpak | [obsidian](roles/obsidian.md) |
| `todotxt` | todo.txt-cli + GNOME Shell extension | GitHub tarball + extensions.gnome.org | [todotxt](roles/todotxt.md) |
| `devpod` | DevPod CLI | GitHub release binary | [devpod](roles/devpod.md) |
| `homelab` | `homelab` command, group, sudo rules, `add` tools | bash function + root-owned tools | [homelab](roles/homelab.md) |

Helper roles that are not in `site.yml` on their own:

| Role | Purpose | Page |
|---|---|---|
| `bashrc_loader` | makes `~/.bashrc` load `~/.bashrc.d/*`; pulled in by `homelab` and `k3s` | [bashrc_loader](roles/bashrc_loader.md) |
| `monitor_app` | registers one application with the monitoring stack; called by other roles | [monitor_app](roles/monitor_app.md) |

## Features

Using the playbook:

- [Running the playbook](features/running-the-playbook.md): layout, tags, settings, preview with `--check --diff`
- [Overwrite policy](features/overwrite-policy.md): which files the playbook rewrites and how they are protected
- [Adding new software](features/adding-software.md): new roles, monitoring hooks, portability

Forgejo and CI:

- [Forgejo Actions runner](features/forgejo-runner.md)
- [Security scanners in CI](features/ci-scanners.md): semgrep, gitleaks, trivy
- [Scan results on the dashboard](features/scan-report.md): `scan-report`
- [Backup, restore and cleanup](features/forgejo-backup.md): `forgejo-backup.yml`

Monitoring:

- [Monitoring other applications](features/monitoring-apps.md): worked example, dashboards, troubleshooting
- [cv-microfrontend on k3s](features/cv-microfrontend.md)

The `homelab` command:

- [The `homelab` command](features/homelab-command.md): `up`, `down`, `status`
- [Group and sudo rules](features/homelab-sudo.md)
- [`homelab add monitoring`](features/homelab-add-monitoring.md)
- [`homelab add documentation`](features/homelab-add-documentation.md)

Platform:

- [Using k3s next to Podman](features/k3s-usage.md)
- [Networking](features/networking.md): what is reachable from where, and how to change it

## Writing docs

One page per role in `docs/roles/<role>.md`, one per feature in
`docs/features/`. When you add a role or feature, add its page and a line to
this index. Comments in role files point at these pages instead of repeating
them.
