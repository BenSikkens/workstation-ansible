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

## Before running: review what will change

Always preview a run before applying it, especially after editing a role or
pulling in someone else's change:

```bash
ansible-playbook site.yml --ask-become-pass --check --diff
```

`--check` runs without making changes; `--diff` shows the exact before/after
of any file this would write. Nothing here will run the risk of silently
clobbering something you can't see coming back.

### Where this playbook can overwrite something, and what's done about it

Most tasks here (`dnf`, `community.general.flatpak`) only install packages —
they never touch your existing configuration or data, so there's nothing to
protect there. The places that *do* write a file outright are:

- The Forgejo/Forgejo-runner Quadlet units (`roles/forgejo/templates/*.j2`,
  deployed via `ansible.builtin.template`) — these are re-rendered and
  reapplied on every run by design, so that changing a default (say, a port
  or image tag) propagates on the next `ansible-playbook` run. They all use
  `backup: true`, so if content changes, Ansible saves a timestamped copy of
  the previous version right next to it before overwriting — nothing is
  ever lost, even if the file does change.
- The Forgejo runner's `config.yml` is the exception: it's only ever written
  **once**, guarded by `when: not forgejo_runner_config_stat.stat.exists` —
  once it exists, the role leaves it alone permanently (this is what holds
  the registration secret, so overwriting it would re-register the runner).
- Forgejo's own application config (`app.ini`, inside the data volume) and
  any vault/repo data are never templated or written by this playbook at
  all — Forgejo manages those itself, so there's nothing here that could
  clobber them.

If you ever hand-edit a Quadlet unit directly on the box, know that the next
playbook run will overwrite it back to the template's version (with a backup
kept) — that's standard Ansible/infrastructure-as-code behavior: the repo is
the source of truth. If you want a hand-edit to stick, make the equivalent
change in the `.j2` template (or the role's `defaults/main.yml`) instead of
editing the deployed file, so the change survives the next run too.

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
| `mkcert` | mkcert | dnf |
| `forgejo` | Forgejo (self-hosted git) + Actions runner | two rootless Podman containers via Quadlet, under a dedicated `git` user |
| `obsidian` | Obsidian | Flatpak (Flathub) |

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

#### Forgejo Actions runner

A second, separate **rootless** container (`forgejo-runner`, image
`code.forgejo.org/forgejo/runner`) runs CI/CD jobs for Forgejo Actions,
under the same `git` user. It's managed the same way — a Quadlet unit at
`~git/.config/containers/systemd/forgejo-runner.container` — and it talks
to Forgejo over a shared Podman network (`forgejo.network`, also deployed
by this role) rather than over the host's published port, so it works
regardless of which host port you've mapped Forgejo to.

**Registration is fully automatic**, no web UI click-through needed:
Forgejo has an "offline registration" CLI mode built for scripted setups
like this one. The role generates a random secret, hands it to Forgejo via
`podman exec ... forgejo-cli actions register --secret ...`, gets back a
UUID, and writes both into the runner's `config.yml` — that file *is* the
registration, so there's no separate token step. This only happens once;
if `config.yml` already exists, the role leaves it alone.

Jobs that use `docker://...` container labels run via the `git` user's own
rootless Podman socket, bind-mounted into the runner container as
`/var/run/docker.sock` — so job containers are themselves rootless, one
level down.

Defaults:

| Variable | Default | Meaning |
|---|---|---|
| `forgejo_runner_image` | `code.forgejo.org/forgejo/runner:latest` | **not version-pinned** — check the registry for a current tag and pin it, the same way `forgejo_image` is pinned |
| `forgejo_runner_name` | the host's hostname | name shown in Forgejo's runner list |
| `forgejo_runner_labels` | `["docker:docker://node:22-bookworm"]` | execution labels workflows can target; add more (e.g. `ubuntu-latest:docker://...`) as needed |
| `forgejo_runner_scope` | `""` (instance-wide) | set to an org/user/repo name to scope the runner narrower |
| `forgejo_runner_data_dir` | `/home/git/forgejo-runner-data` | holds `config.yml` and the generated secret |

Check it directly:
```bash
sudo machinectl shell git@
systemctl --user status forgejo-runner.service
podman logs forgejo-runner
```
It should also show up under Forgejo's **Site Administration → Actions →
Runners**.

### Obsidian

Installed via Flathub (`md.obsidian.Obsidian`), same pattern as
`podman_desktop` — runs natively as a normal desktop window, with vaults
living wherever you choose in your own home directory rather than inside
a container's data volume.
