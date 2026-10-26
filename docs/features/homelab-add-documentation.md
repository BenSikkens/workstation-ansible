# `homelab add documentation`: a project's docs as an Obsidian vault

Tool: `roles/homelab/files/homelab-obsidian` (installed to
`/usr/local/libexec/homelab-obsidian`). Runs as you, without sudo. Part of the
[homelab role](../roles/homelab.md). Needs [Obsidian](../roles/obsidian.md).

```bash
homelab add documentation ~/Repositories/myproject/docs        # a folder with .md files
homelab remove documentation ~/Repositories/myproject/docs
```

`add` registers the folder, where it is, as an Obsidian vault. Nothing is
copied or converted: you edit the project's own Markdown files in Obsidian, and
the edits land in the project.

## Rules

- **Obsidian must be closed.** Obsidian rewrites its vault list when it closes
  and would undo the change. Use `--force` on the tool only if you know what you
  are doing.
- The folder must contain `.md` files (hidden folders, `node_modules`, `venv`
  and `__pycache__` are skipped in that check).
- A folder inside an existing vault, or one that contains an existing vault, is
  refused (nested vaults are confusing).
- Adding a folder that is already a vault changes nothing.
- The old vault list is kept once as `obsidian.json.homelab-backup`.
- The vault is named after the folder, so several projects with a `docs` folder
  all appear as "docs" in Obsidian's vault list (the list shows the paths).
- `remove` forgets the vault; the files are not touched.

## After adding

Start Obsidian and choose the vault under *Manage vaults* (bottom left).
Obsidian creates a `.obsidian/` settings folder inside the vault the first time
it opens it; add `.obsidian/` to the project's `.gitignore` if you do not want
it tracked (the tool reminds you when the folder is in a git repository).

## Flatpak limits

Obsidian runs as a Flatpak (`md.obsidian.Obsidian`) and can only see your home
folder, `/mnt`, `/media` and `/run/media`. A folder elsewhere is registered with
a warning, but Obsidian will not be able to open it.

## Where the list lives

`~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json`. The `vaults`
object is keyed by a 16-character id (a hash of the path) with `path`, `ts` and
`open`. The file is written atomically; if it is not valid JSON, or has an
unexpected layout, the tool refuses to touch it.
