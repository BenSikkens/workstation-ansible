# Role: vscodium

VSCodium (VS Code without Microsoft's telemetry and branding). Tag: `vscodium`.
Source: `roles/vscodium/`.

Follows the official install method for RPM distributions
(<https://vscodium.com/#install>):

1. Imports the repository's GPG key.
2. Adds the `vscodium` yum repository (`https://download.vscodium.com/rpms/`,
   `gpgcheck`, metadata expiry 1 h).
3. Installs the `codium` package with `dnf`.

Updates arrive through normal `dnf upgrade`. RedHat family only. No settings.
