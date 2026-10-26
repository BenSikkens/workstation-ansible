# Running the playbook

`site.yml` is the list of software: one role per piece, in order. Everything
runs against the local machine (`ansible_connection=local`, `inventory.ini`).

## Layout

```
.
├── ansible.cfg           # local defaults (inventory path, callback plugin)
├── inventory.ini         # targets localhost
├── requirements.yml      # external collections (community.general, ansible.posix)
├── site.yml              # main playbook: the list of roles = the list of software
├── forgejo-backup.yml    # restore or remove the pre-install Forgejo backup
├── group_vars/all.yml    # settings you are expected to edit
├── examples/             # example roles that never run by themselves
├── docs/                 # this documentation
└── roles/                # one role per piece of software (see ../roles/)
```

## First run on a fresh machine

```bash
sudo dnf install ansible -y
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml --ask-become-pass
```

`--ask-become-pass` is only needed if your user has no passwordless sudo. (The
[homelab sudo rules](homelab-sudo.md) do not cover Ansible runs.)

## Installing one piece at a time

Every role is tagged with its own name:

```bash
ansible-playbook site.yml --tags k3s --ask-become-pass
ansible-playbook site.yml --tags forgejo,monitoring --ask-become-pass
ansible-playbook site.yml --skip-tags k3s --ask-become-pass   # everything but k3s
ansible-playbook site.yml --list-tags                          # all tags
```

Roles that need another one pull it in themselves, so a tag always works on
its own:

| Role | Pulls in |
|---|---|
| `podman_desktop`, `obsidian` | `flatpak_setup` |
| `homelab`, `k3s` | `bashrc_loader` |

`monitoring` adapts to what exists: the Pushgateway for CI scan results is only
set up when Forgejo is installed, and the Podman exporter only covers users
that exist. If you add Forgejo later, re-run `--tags monitoring`. Likewise,
the [homelab sudo rules](homelab-sudo.md) only cover service users that exist,
so run `--tags homelab` after installing Forgejo or monitoring.

## Settings

Shared settings live in `group_vars/all.yml`:

| Variable | Default | Meaning |
|---|---|---|
| `desktop_user` | the user running Ansible (`$USER`) | whose desktop gets the per-user pieces (todo.txt extension, `homelab`, k3s helpers, kubeconfig) |
| `forgejo_runner_install_semgrep` / `_gitleaks` / `_trivy` | `true` | which scanners the [CI image](ci-scanners.md) contains |
| `forgejo_backup_enabled` | `true` | take a [backup](forgejo-backup.md) of an existing Forgejo before changing it |
| `monitoring_enabled` | `true` | install the [monitoring](../roles/monitoring.md) stack |
| `homelab_users` | (commented example) | who joins the [homelab group](homelab-sudo.md) |

Per-role settings are in each role's `defaults/main.yml`; they are listed on
the role's page. A value in `group_vars/all.yml` wins over a role default.

## Review what will change

Preview a run before applying it, especially after editing a role or pulling in
someone else's change:

```bash
ansible-playbook site.yml --ask-become-pass --check --diff
```

`--check` makes no changes; `--diff` shows the before/after of every file that
would be written. Which files can be overwritten, and what protects them, is
described in [overwrite policy](overwrite-policy.md).

## Related

- [Adding new software](adding-software.md)
- [Overwrite policy](overwrite-policy.md)
- [Role index](../README.md)
