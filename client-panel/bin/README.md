# Required CLI tools for production (install to /usr/local/bin)

Copy these from your production server if missing:

| Tool | Purpose |
|------|---------|
| `wg-client` | Add/remove/enable/disable/renew clients |
| `wg-client-single` | Single-device mode |
| `wg-panel-admin` | CLI user/request management |
| `wg-client-rotate-keys` | Key rotation |
| `wg-client-import-existing` | Import existing `.conf` files |

Example from an existing server:

```bash
scp root@your-server:/usr/local/bin/wg-client client-panel/bin/
scp root@your-server:/usr/local/bin/wg-client-single client-panel/bin/
# ... repeat for other tools
```

All tools must use `/etc/wireguard/` paths (not local dev paths).
