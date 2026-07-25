# Merge request draft — two-hop dataplane performance

## Title

perf: simplify two-hop dataplane, harden MTU/MSS/NAT, and add migrate/diagnose tooling

## Summary

Existing installs could accumulate duplicate iptables NAT/FORWARD/MSS rules, used overly broad entry FORWARD accepts, and lacked a clear migrate/validate path. Combined with undersized or wasteful buffer defaults, this contributed to fragile forwarding and poor TCP behavior on the mandatory two-hop path (`client → entry → exit → internet`).

This change keeps the two-hop architecture, NAT on exit only for production clients, and removes/repairs dataplane clutter. Direct mode remains diagnostic-only. Xray stays optional and off the WireGuard forward path.

## Main changes

### Routing
- Entry `wg-clients` PostUp is route-only (subnet → `wg-clients`)
- Policy table 100 unchanged for twohop egress via `wg-tunnel`
- Entry anti-leak DROP for client→WAN (`WG_ENTRY_ANTILEAK`)
- Direct-mode ACCEPT inserted at priority before DROP

### Firewall and NAT
- Idempotent iptables helpers; install PostUp uses `-C || -A`
- Exit MASQUERADE/FORWARD deduplicated on repair/migrate
- Broad `FORWARD -i/-o wg-clients ACCEPT` removed
- Removed dead `install_exit_proxy_nginx` implementation

### MTU and MSS
- Configurable `WG_SERVER_MTU` / `WG_CLIENTS_MTU` / `WG_TUNNEL_MTU` / client MTUs
- Validation range 1280–1500
- Single MSS clamp-to-PMTU rule; systemd unit collapses duplicates

### Kernel tuning
- Managed `/etc/sysctl.d/99-wg-forward.conf` and `99-wg-performance.conf`
- Raise socket *max* buffers only (no 16MB defaults)
- BBR only when `tcp_bbr` available; conntrack sizing when loaded

### Installation / validation / migration
- Install-time env validation (fail early)
- `deploy/validate-config.sh`
- `deploy/migrate-vpn-stack.sh` with backup + dry-run

### Diagnostics / tests / docs
- `diagnose-vpn.sh` HEALTHY/WARNING/FAILED/N/A
- `tests/test_deploy_helpers.sh`
- Assessment, fresh deployment, performance, architecture updates

## Removed components

| Item | Why safe |
|------|----------|
| Broad wg-clients FORWARD PostUp | Replaced by narrow tunnel forwards + anti-leak |
| `install_exit_proxy_nginx` body | Panels only on entry; function now errors if called |
| `rmem_default`/`wmem_default` = 16MB | Wasteful on small VPS; max buffers remain 64MB |
| Fragile `sysctl.conf` ip_forward append | Replaced by managed drop-in |

## Testing

- `bash tests/test_deploy_helpers.sh` — passed locally
- `python3 -m unittest discover -s tests` — passed locally
- Requires real entry/exit: migrate, diagnose, iperf3 hop tests, public-IP twohop check

## Risks

- Entry anti-leak DROP can break forgotten direct-mode clients until `sync-vpn-modes`
- Migrating PostUp requires interface restart awareness (migrate + fix scripts)
- Distros without BBR warn and continue
- Firewall changes: keep console access

## Rollback

Restore `/etc/wireguard/backups/<ts>-pre-migrate/`, bring interfaces up, run `fix-vpn-routing.sh`.

## Deployment sequence

1. Exit: `migrate-vpn-stack.sh --role exit` → diagnose  
2. Entry: `migrate-vpn-stack.sh --role entry` → diagnose  
3. Renew/verify clients still twohop  
4. Validate public IP = exit  
5. Performance hop tests  
