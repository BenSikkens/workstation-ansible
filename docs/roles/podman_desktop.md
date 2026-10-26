# Role: podman_desktop

Podman Desktop, the GUI for Podman. Tag: `podman_desktop`. Source:
`roles/podman_desktop/`.

Podman Desktop has no official RPM for Fedora; upstream recommends the Flathub
build, so the role installs the Flatpak `io.podman_desktop.PodmanDesktop`
system-wide. Depends on [flatpak_setup](flatpak_setup.md).

It acts on your own user's rootless Podman. Its containers are visible on the
Grafana *Containers* dashboard because the desktop user's Podman is monitored
(see [monitoring](monitoring.md)).

## Settings

None.
