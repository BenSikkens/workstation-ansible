# Role: homelab_gui

A local web dashboard for the [`homelab` command](../features/homelab-command.md):
status of every group, Start/Stop buttons, a log viewer and the links to the
web UIs. Tag: `homelab_gui`. Source: `roles/homelab_gui/`. Depends on
[homelab](homelab.md), so `--tags homelab_gui` works on its own.

It adds no new powers. It calls `homelab status|up|down` and `journalctl` as
your own user, so the [sudo rules](../features/homelab-sudo.md) of the `homelab`
group apply exactly as in a terminal.

## Using it

```bash
homelab gui        # starts the dashboard if needed and opens your browser, signed in
```

or start **Homelab** from the GNOME app grid. The dashboard is at
`http://127.0.0.1:8088` (loopback only).

## What it shows

- One card per installed group (identity, forgejo, monitoring, k3s) with the state of every unit, **Start** and **Stop** for that group, and links to its web UI (Authelia, lldap, Forgejo, Grafana).
- **Start all** / **Stop all** (stop asks for confirmation). Output of the running action streams into a panel; only one action runs at a time.
- A log viewer: pick a unit, last 300 lines, refreshed every 3 seconds while "Follow" is on.
- The output of `identity-info` (URLs, base DN, where the CA certificate is). Passwords are never shown; the page prints the `sudo cat` command instead.

Groups that are not installed are listed as "Not installed", like `homelab status` does.

## What it installs

| What | Where |
|---|---|
| server and page (Python standard library, no packages) | `~/.local/lib/homelab-gui/` |
| settings (port, links) | `~/.config/homelab-gui/config.json` |
| access token (0600, created once, never overwritten) | `~/.config/homelab-gui/token` |
| `homelab-gui` launcher | `~/.local/bin/homelab-gui` |
| desktop entry | `~/.local/share/applications/homelab.desktop` (`Icon=homelab`) |
| icon | `~/.local/share/icons/hicolor/scalable/apps/homelab.svg` (or `512x512/apps/homelab.png` for a custom PNG) |
| systemd user service | `~/.config/systemd/user/homelab-gui.service` |

## Changing the icon

The built-in icon is `roles/homelab_gui/files/homelab.svg` (a small server rack,
status lights included); edit it or replace it. To use an image from elsewhere,
set in `group_vars/all.yml`:

```yaml
homelab_gui_icon: /home/you/Pictures/homelab.svg   # .svg, or a square .png of 256 px or more
```

and run `ansible-playbook site.yml --tags homelab_gui --ask-become-pass`. An SVG
is crisp at every size and is the better choice. If GNOME still shows the old
icon, log out and in again (or press Alt+F2, `r`, Enter on X11).

## Security

Anything on the machine can reach a loopback port, so:

- Every request needs a secret cookie. `homelab gui` opens `/login?t=<token>` once; the page sets an HttpOnly, SameSite=Strict cookie. Without it the server answers 401. (The token is briefly visible in the browser's history and in the `xdg-open` command line, to local users only.)
- The `Host` header must be `127.0.0.1:<port>` or `localhost:<port>` (blocks DNS rebinding); POSTs also need a custom header and a matching `Origin` (blocks CSRF from other websites).
- The only actions are `up` and `down` with a fixed list of scopes. Log targets are checked against what `homelab status` reported; nothing from the request reaches a shell.
- The service deliberately has no `NoNewPrivileges=`, because `homelab` calls `sudo`.

To rotate the token: delete `~/.config/homelab-gui/token`, run the playbook again (`--tags homelab_gui`), then `homelab gui`.

## Good to know

- Passwordless sudo needs the `homelab` group in the dashboard's session. After the first playbook run, log out and in again; until then the page shows a warning.
- Logs come from `journalctl` as you. Members of `wheel` or `systemd-journal` can read the service users' journals (the default on Fedora Workstation); the log panel says so if not.
- The page refreshes every 5 seconds only while its tab is visible.

## Settings (`roles/homelab_gui/defaults/main.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `homelab_gui_port` | `8088` | loopback port |
| `homelab_gui_autostart` | `true` | start it at login; `false` = only when `homelab gui` is run |
| `homelab_gui_log_lines` | `300` | lines loaded by the log viewer |
| `homelab_gui_icon` | empty (built-in) | path of your own `.svg` or `.png` launcher icon |
| `homelab_gui_links` | Authelia, lldap, Forgejo, Grafana | links on the cards |
