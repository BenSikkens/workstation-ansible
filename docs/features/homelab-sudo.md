# The `homelab` group and its sudo rules

Part of the [homelab role](../roles/homelab.md); template:
`roles/homelab/templates/homelab.sudoers.j2`, installed as
`/etc/sudoers.d/homelab`.

The `homelab` command needs `sudo` to reach the service users' systemd
instances and to run k3s. The role creates a group (`homelab_group`, default
`homelab`), adds the users in `homelab_users` (default: `desktop_user`) and
installs the sudoers file. Members get passwordless sudo for the **exact command
lines** `homelab` uses and nothing else; everyone else is asked for a password
as before. A new group membership applies after logging out and in once.

The rules are generated from `roles/homelab/vars/main.yml`, one entry per unit
and verb, and `visudo -cf` checks the file before it is installed. If the check
fails, the file is not installed.

## What members can do

- start, stop and read the status of the listed units: Forgejo, the runner, the
  Podman socket, Pushgateway, exporter, Prometheus, Loki, Grafana, Alloy, k3s
  (Grafana may also be restarted, for `homelab add monitoring`);
- list and stop `git`'s running containers (one wildcard, limited to
  `podman stop --time 10 *`);
- run `k3s-killall.sh` and `k3s kubectl get --raw=/readyz`;
- run `homelab-monitoring apply`, which takes no arguments and only reads the
  drop folder of [homelab add monitoring](homelab-add-monitoring.md);
- read the k3s kubeconfig (see the warning below).

They cannot edit units, run other commands as the service users, or start new
containers.

## How the rules are kept tight

- Each rule is a full command line with fixed arguments, e.g.
  `/usr/bin/env XDG_RUNTIME_DIR=/run/user/<uid> systemctl --user start forgejo.service`
  run as the service user. A command with no argument list in sudoers would
  allow any arguments, so commands that take none are pinned with an empty
  argument (`""`).
- The service users' uid is pinned in the rule, so a user that does not exist
  yet gets no rules.
- `=` is escaped (`\=`) so sudoers does not read it as an assignment.
- Nothing a member types ever reaches `sudo` as an argument beyond the one
  stop-wildcard above. The `add monitoring` flow uses a drop folder for exactly
  this reason.

## Seeing and testing the rules

```bash
sudo -l -U <user>        # what the user may run
sudo visudo -cf /etc/sudoers.d/homelab
```

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `homelab_group` | `homelab` | the group |
| `homelab_users` | `[ "{{ desktop_user }}" ]` | members the role adds |
| `homelab_sudo_k3s_kubeconfig` | `true` | passwordless `cat` of the k3s kubeconfig |

Add people in `group_vars/all.yml`:

```yaml
homelab_users:
  - alice
  - bob
```

### Adding yourself by hand (shortcut)

If you only want to add a user without running Ansible:

```bash
sudo usermod -aG homelab <user>      # then log out and in again
```

This only works once the role has created the group and the sudoers file.

## Two things to know

- **Run the role after installing services.** The rules pin the service users'
  uid, so a user that does not exist yet gets no rules. After installing Forgejo
  or monitoring, run `ansible-playbook site.yml --tags homelab --ask-become-pass`
  once.
- **The k3s kubeconfig rule is effectively root.** `homelab up k3s` copies the
  cluster-admin kubeconfig, so one rule (`cat` of `/etc/rancher/k3s/k3s.yaml`)
  lets the member read that credential, and whoever holds it can start a
  privileged pod. Members should be people you would give root to anyway. Set
  `homelab_sudo_k3s_kubeconfig: false` to drop that rule; the kubeconfig copy
  then asks for a password instead.

If you change what `homelab` runs through sudo, update the unit table in
`roles/homelab/vars/main.yml` as well.
