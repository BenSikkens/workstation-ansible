# Workstation Setup

Ansible playbook to reproduce my software setup on a fresh Fedora install
(or, since it is Ansible, in principle any Linux distro; see
[adding new software](docs/features/adding-software.md) for portability).

One role per piece of software, listed in `site.yml`. Every role and feature is
documented in **[docs/](docs/README.md)**.

## Quick start

```bash
sudo dnf install ansible -y
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml --check --diff --ask-become-pass   # preview
ansible-playbook site.yml --ask-become-pass                  # apply
```

Install one piece at a time with its tag, for example
`ansible-playbook site.yml --tags k3s --ask-become-pass`
(`--list-tags` shows them all). Details:
[running the playbook](docs/features/running-the-playbook.md) and
[overwrite policy](docs/features/overwrite-policy.md).

## What is installed

| Role | Software | Docs |
|---|---|---|
| `flatpak_setup` | Flatpak + Flathub (base for the Flatpak apps) | [page](docs/roles/flatpak_setup.md) |
| `podman_desktop` | Podman Desktop (Flatpak) | [page](docs/roles/podman_desktop.md) |
| `vim` | Vim, set as the default editor | [page](docs/roles/vim.md) |
| `vscodium` | VSCodium | [page](docs/roles/vscodium.md) |
| `keepassxc` | KeePassXC | [page](docs/roles/keepassxc.md) |
| `mkcert` | mkcert | [page](docs/roles/mkcert.md) |
| `forgejo` | Forgejo git server + Actions runner + scanner CI image | [page](docs/roles/forgejo.md) |
| `monitoring` | Grafana, Prometheus, Loki, Alloy, exporters | [page](docs/roles/monitoring.md) |
| `k3s` | single-node Kubernetes next to Podman | [page](docs/roles/k3s.md) |
| `obsidian` | Obsidian (Flatpak) | [page](docs/roles/obsidian.md) |
| `todotxt` | todo.txt-cli + GNOME Shell extension | [page](docs/roles/todotxt.md) |
| `devpod` | DevPod CLI | [page](docs/roles/devpod.md) |
| `homelab` | `homelab` command, group, sudo rules | [page](docs/roles/homelab.md) |
| `bashrc_loader`, `monitor_app` | helper roles | [page](docs/roles/bashrc_loader.md), [page](docs/roles/monitor_app.md) |

## Everyday commands

```bash
homelab up | down | status [forgejo|monitoring|k3s]
homelab add monitoring ~/Repositories/myproject/monitoring
homelab add documentation ~/Repositories/myproject/docs
```

See [the homelab command](docs/features/homelab-command.md).

## Where to read more

The full index, with every feature page (Forgejo runner and scanners, backup,
monitoring other applications, networking, k3s, sudo rules), is
[docs/README.md](docs/README.md).
