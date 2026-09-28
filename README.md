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
| `mkcert` | mkcert | dnf |
| `forgejo` | Forgejo (self-hosted git) + Actions runner | two rootless Podman containers via Quadlet, under a dedicated `git` user |
| `obsidian` | Obsidian | rootless Podman container via Quadlet, under a dedicated `obsidian` user |

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

Obsidian is a native desktop app with no official container image, so
there's no clean way to run it rootlessly without forwarding the host's
X11/Wayland socket into the container — which defeats the isolation the
"rootless container" ask is for. Instead this role uses
[linuxserver.io's Obsidian image](https://docs.linuxserver.io/images/docker-obsidian/),
which serves a full desktop over the browser (via KasmVNC) — you open
`http://localhost:8484` and get Obsidian running in a virtual desktop,
fully contained, no host display integration required.

Runs as a **rootless** Podman container under a dedicated `obsidian` user,
managed the same way as Forgejo: a Quadlet unit at
`~obsidian/.config/containers/systemd/obsidian.container`, with systemd
lingering enabled so it survives reboots.

Defaults (override in `roles/obsidian/defaults/main.yml` or via
`group_vars/all.yml`):

| Variable | Default | Meaning |
|---|---|---|
| `obsidian_user` | `obsidian` | system user the container runs as |
| `obsidian_image` | `lscr.io/linuxserver/obsidian:latest` | web-desktop image bundling Obsidian |
| `obsidian_data_dir` | `/home/obsidian/obsidian-data` | persistent config + vaults on the host |
| `obsidian_http_port` | `8484` | web desktop (picked to avoid clashing with Forgejo's 3000) |
| `obsidian_https_port` | `8485` | web desktop over https (self-signed) |
| `obsidian_timezone` | `Etc/UTC` | container `TZ`, set this to your own timezone |

After running the playbook:

- Open `http://localhost:8484` in a browser — you'll land in a virtual
  desktop with Obsidian ready to open or create a vault
- Vaults and app config persist under `{{ obsidian_data_dir }}/config` on
  the host
- Check the service directly:
  ```bash
  sudo machinectl shell obsidian@
  systemctl --user status obsidian.service
  podman logs obsidian
  ```

**Note:** if you'd rather run Obsidian natively (not containerized) with
your vault living directly in your home directory, Flatpak (`md.obsidian.Obsidian`
on Flathub) is the simpler path — say so and I'll swap this role for that.
