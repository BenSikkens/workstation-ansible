# Role: obsidian

Obsidian, the Markdown note-taking app. Tag: `obsidian`. Source:
`roles/obsidian/`.

Installed from Flathub (`md.obsidian.Obsidian`), same pattern as
[podman_desktop](podman_desktop.md); depends on
[flatpak_setup](flatpak_setup.md). It runs as a normal desktop window, with
vaults living wherever you choose in your own home directory rather than inside
a container's data volume. The Flatpak can see your home folder, `/mnt`,
`/media` and `/run/media`.

## Project docs as vaults

[`homelab add documentation`](../features/homelab-add-documentation.md)
registers a project's `docs` folder as a vault.

## Settings

None.
