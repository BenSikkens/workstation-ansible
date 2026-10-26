# Role: flatpak_setup

Base dependency for every role that installs software from Flathub.
Tag: `flatpak_setup`. Source: `roles/flatpak_setup/`.

## What it does

1. Installs the `flatpak` package with `dnf` (RedHat family only).
2. Adds the Flathub remote (`https://dl.flathub.org/repo/flathub.flatpakrepo`)
   system-wide. Fedora ships flatpak but does not enable Flathub by default.

## Used by

[podman_desktop](podman_desktop.md) and [obsidian](obsidian.md) declare it in
their `meta/main.yml`, so `--tags podman_desktop` or `--tags obsidian` works on
its own.

## Settings

None.
