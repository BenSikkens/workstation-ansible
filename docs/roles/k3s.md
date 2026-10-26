# Role: k3s

A single-node Kubernetes (server and agent in one) as a system service next to
the rootless Podman containers. Tag: `k3s`. Source: `roles/k3s/`. Depends on
[bashrc_loader](bashrc_loader.md). Usage: [using k3s](../features/k3s-usage.md).

## What it does

1. **Kernel:** loads `overlay` and `br_netfilter` now and at boot; applies the
   sysctls in `k3s_sysctl` (`/etc/sysctl.d/90-k3s.conf`).
2. **firewalld** (if running and `k3s_manage_firewalld`): puts the pod and
   service CIDRs in the `trusted` zone. Nothing on the LAN is opened.
3. **Install:** downloads the official installer (`https://get.k3s.io`) and runs
   it as root, pinned with `INSTALL_K3S_VERSION`, with start and enable
   **skipped**. It installs the binary, the `k3s-selinux` policy, the systemd
   unit and `k3s-killall.sh` / `k3s-uninstall.sh`. Skipped when the installed
   version already matches.
4. **Config:** renders `/etc/rancher/k3s/config.yaml` (root, 0600, with backup).
5. **Service:** enabled at boot only when `k3s_autostart` is true. Started only
   then. A running k3s is restarted when the version or config changed; a
   stopped one stays stopped.
6. **Your user:** creates `~/.kube`, copies the kubeconfig if k3s has already
   started once, and writes the `~/.bashrc.d/k3s.sh` drop-in (`KUBECONFIG`,
   kubectl completion, `k3s-load`).

## Settings (`roles/k3s/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `k3s_version` | `v1.34.12+k3s1` | pinned; changing it upgrades in place |
| `k3s_autostart` | `false` | `true` = enabled at boot and started; `false` = use `homelab up k3s` |
| `k3s_cluster_cidr` / `k3s_service_cidr` | `10.42.0.0/16` / `10.43.0.0/16` | must not overlap Podman's `10.88.0.0/16` or the `10.89.x` Quadlet networks |
| `k3s_disable` | `[]` | add-ons to switch off, e.g. `[traefik, servicelb]` (those two publish 80 and 443) |
| `k3s_config_extra` | `{}` | anything else for `config.yaml`, e.g. `{node-name: homelab}` |
| `k3s_manage_firewalld` | `true` | trusted-zone entries |
| `k3s_sysctl` | ip_forward, bridge-nf-call-*, inotify limits | |
| `k3s_selinux` | on when SELinux is enabled | adds `selinux: true` to the config |
| `k3s_kubeconfig_path` | `/home/<desktop_user>/.kube/k3s.yaml` | your copy of the kubeconfig |

## Related

- [homelab command](../features/homelab-command.md) starts and stops it.
- [networking](../features/networking.md) lists the ports it opens.
- [cv-microfrontend](../features/cv-microfrontend.md) is the one workload
  monitored.
