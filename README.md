# Workstation Setup

Ansible playbook to reproduce my software setup on a fresh Fedora install
(or, since it's Ansible, in principle any Linux distro — see notes below).

## Layout

```
.
├── ansible.cfg          # local defaults (inventory path, callback plugin)
├── inventory.ini         # targets localhost by default
├── requirements.yml       # external collections (community.general for flatpak)
├── site.yml              # main playbook — the list of roles = the list of software
└── roles/
    ├── flatpak_setup/     # base dependency: installs flatpak, adds Flathub remote
    └── podman_desktop/    # installs Podman Desktop via Flathub
```

## Usage

One-time setup on a fresh machine:

```bash
sudo dnf install ansible -y
ansible-galaxy collection install -r requirements.yml
```

Run the playbook:

```bash
ansible-playbook site.yml
```

If your user doesn't have passwordless sudo configured, add `--ask-become-pass`.

## Adding new software

1. Create a new role: `ansible-galaxy init roles/<name> --offline` (or just make
   `roles/<name>/tasks/main.yml` by hand — that's all that's strictly needed).
2. Write the install task(s) — prefer `ansible.builtin.dnf` for RPM packages,
   `community.general.flatpak` for Flatpak apps.
3. Add the role name to the `roles:` list in `site.yml`.

## Notes on portability across distros

This is currently Fedora-first (uses `dnf` directly in `flatpak_setup`).
To make a role portable to Debian/Arch/etc. later, either:
- Guard package-manager tasks with `when: ansible_facts['os_family'] == "RedHat"`
  and add sibling tasks for other families, or
- Prefer Flatpak for GUI apps where possible, since that layer is already
  distro-agnostic once `flatpak_setup` has run.

## Software installed so far

| Role | Software | Install method |
|---|---|---|
| `podman_desktop` | Podman Desktop | Flatpak (Flathub) |
| `vim` | Vim (vim-enhanced) | dnf |
| `vscodium` | VSCodium | dnf (official VSCodium RPM repo) |
| `keepassxc` | KeePassXC | dnf |
| `forgejo` | Forgejo (self-hosted git) | rootless Podman container via Quadlet, under a dedicated `git` user |

### Forgejo (self-hosted git server)

Runs as a **rootless** Podman container under a dedicated `git` system user,
managed as a systemd **user** service via a [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
unit at `~git/.config/containers/systemd/forgejo.container`. Systemd lingering
is enabled for `git` so the service survives reboots without anyone logging
in as that user.

Defaults (override in `roles/forgejo/defaults/main.yml` or via
`group_vars/all.yml`):

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_user` | `git` | system user the container runs as |
| `forgejo_image` | `codeberg.org/forgejo/forgejo:10` | pinned to major version 10, not `latest` |
| `forgejo_data_dir` | `/home/git/forgejo-data` | persistent data on the host |
| `forgejo_http_port` | `3000` | web UI |
| `forgejo_ssh_port` | `2222` | git-over-ssh (not 22 — that's the host's own sshd, and rootless containers can't bind ports <1024 on the host side) |

After running the playbook:

- Web UI / first-run setup wizard: `http://localhost:3000`
- Clone over SSH: `git clone ssh://git@localhost:2222/<owner>/<repo>.git`
  (you'll want an entry in your `~/.ssh/config` for the non-standard port)
- Check the service directly:
  ```bash
  sudo machinectl shell git@ 
  systemctl --user status forgejo.service
  podman logs forgejo
  ```

**Note:** this scaffold gets the container running and persistent — it
doesn't configure Forgejo itself (admin account, `APP_URL`, etc.). That's
done once through the first-run web wizard, or later by editing
`{{ forgejo_data_dir }}/data/gitea/conf/app.ini` inside the data volume.
