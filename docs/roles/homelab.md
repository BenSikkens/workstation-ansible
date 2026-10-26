# Role: homelab

The `homelab` command, the `homelab` group and its sudo rules, and the tools
behind `homelab add`. Tag: `homelab`. Source: `roles/homelab/`. Depends on
[bashrc_loader](bashrc_loader.md). Listed last in `site.yml` so that the
service users it covers already exist.

## What it installs

| What | Where |
|---|---|
| the `homelab` shell function and completion | `~/.bashrc.d/homelab.sh` for `desktop_user` (no backup copy; the directory is sourced) |
| `homelab-monitoring` (root-owned) | `/usr/local/libexec/homelab-monitoring` |
| `homelab-obsidian` | `/usr/local/libexec/homelab-obsidian` |
| settings for `homelab-monitoring` | `/etc/homelab/monitoring.json` |
| drop folder for `homelab add monitoring` | `/var/lib/homelab/monitoring`, writable by the group |
| the group (`homelab`) and its members | `homelab_users` |
| sudo rules | `/etc/sudoers.d/homelab`, validated with `visudo -cf` |
| PyYAML | `dnf` package, used by the tools to parse data source files |

Before writing the sudoers file the role checks that `k3s` and
`k3s-killall.sh` are owned by root and not writable by group or others (a
writable file behind a sudo rule would be a hole); it fails otherwise.

## Features

- [the `homelab` command](../features/homelab-command.md): `up`, `down`, `status`
- [group and sudo rules](../features/homelab-sudo.md)
- [`homelab add monitoring`](../features/homelab-add-monitoring.md)
- [`homelab add documentation`](../features/homelab-add-documentation.md)

## Settings (`roles/homelab/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `homelab_group` | `homelab` | group allowed to use the commands without a password |
| `homelab_users` | `[desktop_user]` | members |
| `homelab_sudo_k3s_kubeconfig` | `true` | passwordless read of the k3s kubeconfig (effectively root) |
| `homelab_forgejo_user`, `homelab_monitoring_user` | follow the roles | which accounts the rules cover |
| `homelab_forgejo_http_port`, `homelab_grafana_port` | follow the roles | ports in the printed URLs |
| `homelab_k3s_bin`, `homelab_k3s_killall`, `homelab_k3s_kubeconfig_src` | `/usr/local/bin/k3s`, `/usr/local/bin/k3s-killall.sh`, `/etc/rancher/k3s/k3s.yaml` | |
| `homelab_k3s_kubeconfig` | `~/.kube/k3s.yaml` | your copy |
| `homelab_libexec_dir` | `/usr/local/libexec` | |
| `homelab_dropbox_dir` | `/var/lib/homelab/monitoring` | |
| `homelab_monitoring_config_dir` | the monitoring role's directory | |

`roles/homelab/vars/main.yml` holds the table of units (and the verbs allowed
for each) that drives both the command and the sudo rules; it is not meant to be
overridden. What is installed is **not** configured here: the command detects
it at run time.

Re-run `--tags homelab` after installing Forgejo or monitoring, so their users
get rules.
