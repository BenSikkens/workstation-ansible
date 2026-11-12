# Role: postman

Postman, the API client. Tag: `postman`. Source: `roles/postman/`.

Installed system-wide from Flathub (`com.getpostman.Postman`); Postman does not
ship an RPM. Depends on [flatpak_setup](flatpak_setup.md), so `--tags postman`
works on its own. Updates come with `flatpak update`. Postman is proprietary
software and its account sign-in is optional for local use.

The Flatpak is sandboxed. Requests to services on this machine use
`localhost:<port>`. Apps with certificates from the local mkcert CA (such as
the [identity stack](../features/identity-oidc-for-apps.md)) are only trusted
if the CA is available inside the sandbox; otherwise turn off certificate
verification in Postman's settings for those requests. Not tested.

## Settings

None.
