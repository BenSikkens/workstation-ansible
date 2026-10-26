# The `homelab` command: switch the stack on and off

Installed by the [homelab role](../roles/homelab.md) for your desktop user
(`desktop_user`) as a bash function in `~/.bashrc.d/homelab.sh`, which Fedora's
`~/.bashrc` already sources (the [bashrc_loader](../roles/bashrc_loader.md)
role makes sure of that). It exists because the stack holds resources even when
idle.

```bash
homelab up                  # start everything that is installed
homelab down                # stop it all, plus any CI containers left behind
homelab status              # running / degraded / stopped, per unit
homelab up k3s              # only the k3s cluster
homelab down forgejo        # only Forgejo + runner (monitoring keeps running)
homelab status monitoring   # only Grafana, Prometheus, Loki, Alloy, ...
```

The optional scope is `forgejo`, `monitoring`, `k3s` or `all` (default).
The command only appears in **new** shells; in an open terminal run
`source ~/.bashrc.d/homelab.sh`. Tab completion is included.

Two more verb pairs add a project's own material, see
[homelab add monitoring](homelab-add-monitoring.md) and
[homelab add documentation](homelab-add-documentation.md).

## What it manages is detected every time

It asks systemd which units exist, so it reflects the machine, not what the
playbook last did: a piece you installed or removed by hand, or with `--tags`,
is picked up on the next command, with no re-run of the `homelab` role. `all`
covers whatever is installed and prints `Not installed: ...` for the rest;
naming a scope that is not installed says so and exits 2. Only settings (the
service user names and the ports in the printed URLs) are written by Ansible.

## What each scope covers

| Scope | Units |
|---|---|
| `forgejo` | `forgejo`, `forgejo-runner` (user `git`); plus the Podman socket, Pushgateway and Podman exporter |
| `monitoring` | `prometheus`, `loki`, `grafana` (user `monitoring`); `alloy.service` (system) |
| `k3s` | `k3s.service` |

The exact list, with the verbs allowed for each, is in `roles/homelab/vars/main.yml`.

## Exit codes

`status` exits 0 when everything in scope is running, 1 when degraded and 3
when stopped, so it is usable in scripts. A group counts as running when its
core units are up (Forgejo + runner; Prometheus, Loki, Grafana and Alloy; k3s).
The Pushgateway and the Podman exporters are listed but do not make a group
"degraded" on their own.

## Details

- `homelab down forgejo` leaves the Pushgateway and the Podman socket alone
  while monitoring is installed, so monitoring keeps working.
- `homelab up k3s` waits until the API answers, then refreshes your copy of the
  kubeconfig (`~/.kube/k3s.yaml`). See [using k3s](k3s-usage.md).
- `homelab down k3s` runs `k3s-killall.sh`. A plain `systemctl stop k3s` leaves
  every pod's container running (by design, so k3s can be upgraded without
  downtime), which defeats the point of switching it off.
- `homelab down` is a runtime switch only. Forgejo and monitoring are enabled
  and their service users have lingering on, so they come back at the next
  boot (and `ansible-playbook` starts them if they are down). k3s is the
  exception: it is not enabled at boot unless you set `k3s_autostart: true`.

## Password prompts

The command uses `sudo` to reach the service users' systemd instances and to
run k3s. Members of the `homelab` group do this without a password, for exactly
those command lines; see [homelab sudo rules](homelab-sudo.md).
