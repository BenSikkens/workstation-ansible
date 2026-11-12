# Role: dbeaver

DBeaver Community, a graphical client for PostgreSQL, MySQL/MariaDB, SQLite and
many other databases. Tag: `dbeaver`. Source: `roles/dbeaver/`.

Installed system-wide from Flathub (`io.dbeaver.DBeaverCommunity`); there is no
Fedora RPM. Depends on [flatpak_setup](flatpak_setup.md), so
`--tags dbeaver` works on its own. Updates come with `flatpak update`.

The Flatpak runs sandboxed. To connect to a database in a local container,
use the published host port (`localhost:<port>`); SQLite files must live in
your home folder or another path the Flatpak can see.

## Settings

None.
