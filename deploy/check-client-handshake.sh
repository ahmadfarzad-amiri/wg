#!/usr/bin/env bash
# Diagnose client ↔ entry WireGuard handshake (wg-clients).
#
# Usage:
#   sudo wg-ops check-client
#   sudo bash deploy/check-client-handshake.sh
set -eo pipefail

if [[ -z "${WG_DEPLOY_REEXEC:-}" && ! -t 0 ]]; then
  export WG_DEPLOY_REEXEC=1
  if [[ -z "${GITHUB_RAW_BASE:-}" ]]; then
    if [[ -n "${WG_RAW_BASE:-}" ]]; then
      GITHUB_RAW_BASE="$WG_RAW_BASE"
    elif [[ -n "${WG_VERSION:-}" ]]; then
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v${WG_VERSION#v}"
    else
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest"
    fi
  fi
  _WG_INSTALLER="$(mktemp /tmp/wg-check-client-XXXXXX.sh)"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/check-client-handshake.sh" -o "$_WG_INSTALLER"
  chmod 700 "$_WG_INSTALLER"
  exec bash "$_WG_INSTALLER" "$@"
fi

_WG_SCRIPT=""
if [[ "${BASH_SOURCE[0]+set}" == "set" ]]; then
  _WG_SCRIPT="${BASH_SOURCE[0]}"
fi
if [[ -n "$_WG_SCRIPT" && -f "$(dirname "$_WG_SCRIPT")/lib/common.sh" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$_WG_SCRIPT")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
else
  _BOOT="$(mktemp -d)"
  mkdir -p "$_BOOT/deploy/lib"
  if [[ -z "${GITHUB_RAW_BASE:-}" ]]; then
    if [[ -n "${WG_RAW_BASE:-}" ]]; then
      GITHUB_RAW_BASE="$WG_RAW_BASE"
    elif [[ -n "${WG_VERSION:-}" ]]; then
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@v${WG_VERSION#v}"
    else
      GITHUB_RAW_BASE="https://cdn.jsdelivr.net/gh/ahmadfarzad-amiri/wg@latest"
    fi
  fi
  curl -fsSL "$GITHUB_RAW_BASE/deploy/repo.conf" -o "$_BOOT/deploy/repo.conf"
  curl -fsSL "$GITHUB_RAW_BASE/deploy/lib/common.sh" -o "$_BOOT/deploy/lib/common.sh"
  SCRIPT_DIR="$_BOOT/deploy"
  # shellcheck source=lib/common.sh
  source "$SCRIPT_DIR/lib/common.sh"
fi
set -u
require_root
require_entry_server

if [[ -f /etc/wireguard/entry-server.env ]]; then
  # shellcheck disable=SC1091
  source /etc/wireguard/entry-server.env
fi

CLIENT_IF="${WG_CLIENT_IF:-wg-clients}"
CLIENT_DIR="${WG_CLIENT_DIR:-/etc/wireguard/clients}"
ENDPOINT_FILE="/etc/wireguard/wg-endpoint"
SERVER_PUB_FILE="/etc/wireguard/clients-server.pub"
WAN_IF="$(default_route_iface)"
WAN_IF="${WAN_IF:-eth0}"

client_port="${WG_CLIENT_PORT:-51820}"
if [[ -f "$ENDPOINT_FILE" ]]; then
  _ep="$(tr -d '[:space:]' <"$ENDPOINT_FILE")"
  [[ "$_ep" == *:* ]] && client_port="${_ep##*:}"
fi

log "=== ENTRY client handshake check (wg-clients) ==="
wg_ensure_clients_udp_input 2>/dev/null || true

if [[ -f "$ENDPOINT_FILE" ]]; then
  log "wg-endpoint         : $(tr -d '[:space:]' <"$ENDPOINT_FILE")"
else
  warn "Missing $ENDPOINT_FILE"
fi

listen_port="$(wg show "$CLIENT_IF" listen-port 2>/dev/null || true)"
log "Live ListenPort     : ${listen_port:-(iface down)}"
log "Expected client UDP : ${client_port}"

file_pub=""
live_pub=""
if [[ -f "$SERVER_PUB_FILE" ]]; then
  file_pub="$(tr -d '[:space:]' <"$SERVER_PUB_FILE")"
fi
live_pub="$(wg show "$CLIENT_IF" public-key 2>/dev/null | tr -d '[:space:]' || true)"
log "clients-server.pub  : ${file_pub:-(missing)}"
log "live ${CLIENT_IF} pub : ${live_pub:-(none)}"

if [[ -n "$file_pub" && -n "$live_pub" && "$file_pub" != "$live_pub" ]]; then
  warn "PUBKEY MISMATCH — every client .conf Peer PublicKey is wrong until repaired:"
  warn "  printf '%s\\n' \"\$(wg show ${CLIENT_IF} public-key)\" | sudo tee ${SERVER_PUB_FILE}"
  warn "  then renew/re-create client configs and re-import on devices"
elif [[ -n "$file_pub" && -n "$live_pub" ]]; then
  log "Pubkey file == live : OK"
fi

sample_conf="$(ls -1 "${CLIENT_DIR}"/*.conf 2>/dev/null | head -1 || true)"
if [[ -n "$sample_conf" ]]; then
  sample_pub="$(awk -F'= *' '/^\[Peer\]/{p=1;next} p && /^PublicKey[[:space:]]*=/{print $2; exit}' "$sample_conf" | tr -d '[:space:]')"
  sample_ep="$(awk -F'= *' '/^\[Peer\]/{p=1;next} p && /^Endpoint[[:space:]]*=/{print $2; exit}' "$sample_conf" | tr -d '[:space:]')"
  log "Sample conf         : $(basename "$sample_conf")"
  log "  Peer PublicKey    : ${sample_pub:-(missing)}"
  log "  Endpoint          : ${sample_ep:-(missing)}"
  if [[ -n "$sample_pub" && -n "$live_pub" && "$sample_pub" != "$live_pub" ]]; then
    warn "Sample conf Peer PublicKey != live server — re-import after renew"
  fi
  if [[ -f "$ENDPOINT_FILE" && -n "$sample_ep" ]]; then
    want_ep="$(tr -d '[:space:]' <"$ENDPOINT_FILE")"
    if [[ "$sample_ep" != "$want_ep" ]]; then
      warn "Sample Endpoint != wg-endpoint — run: sudo wg-ops fix-endpoint ${want_ep}"
    fi
  fi
else
  warn "No configs under ${CLIENT_DIR}"
fi

echo
log "iptables INPUT udp/${client_port}:"
iptables -L INPUT -n -v 2>/dev/null | grep -E "udp.*dpt:${client_port}|dpt:${client_port}" \
  || warn "No INPUT rule matched for udp/${client_port}"

echo
ok=0
oneway=0
never=0
if ! wg show "$CLIENT_IF" >/dev/null 2>&1; then
  die "Interface ${CLIENT_IF} is not up. Run: sudo wg-ops start  (or fix-routing --role entry)"
fi

while read -r pub; do
  [[ -n "$pub" ]] || continue
  rx="$(wg show "$CLIENT_IF" transfer 2>/dev/null | awk -v k="$pub" '$1==k {print $2+0; exit}')"
  tx="$(wg show "$CLIENT_IF" transfer 2>/dev/null | awk -v k="$pub" '$1==k {print $3+0; exit}')"
  hs="$(wg show "$CLIENT_IF" latest-handshakes 2>/dev/null | awk -v k="$pub" '$1==k {print $2+0; exit}')"
  ep="$(wg show "$CLIENT_IF" endpoints 2>/dev/null | awk -v k="$pub" '$1==k {print $2; exit}')"
  rx="${rx:-0}"; tx="${tx:-0}"; hs="${hs:-0}"
  short="${pub:0:20}…"
  if [[ "$hs" -gt 0 ]]; then
    log "OK     ${short}  hs=${hs} rx=${rx} tx=${tx} ep=${ep:-(none)}"
    ok=$((ok + 1))
  elif [[ "$rx" -gt 0 && "$tx" -gt 0 ]]; then
    warn "ONE-WAY ${short}  rx=${rx} tx=${tx} hs=0 ep=${ep:-(none)} — server answered; client did not complete"
    oneway=$((oneway + 1))
  else
    warn "NEVER  ${short}  rx=${rx} tx=${tx} hs=0 — no initiation reached entry (or peer unused)"
    never=$((never + 1))
  fi
done < <(wg show "$CLIENT_IF" peers 2>/dev/null || true)

echo
log "Summary: handshake_ok=${ok} one_way=${oneway} never_contacted=${never}"

if [[ "$oneway" -gt 0 ]]; then
  cat <<EOF

ONE-WAY means WireGuard on this host received initiations and sent responses,
but the client never completed the handshake (latest-handshakes stays 0).

1) Confirm keys (above pubkey triple must match).
2) Re-download/re-import the CURRENT .conf from the panel (not an old QR).
3) While the client is connecting, watch the WAN NIC:
     sudo tcpdump -ni ${WAN_IF} udp port ${client_port} -c 20
   Expect pairs: client→entry length 148, then entry→client length 92.
4) Same .conf on another network (Wi‑Fi ↔ mobile, or a different ISP).
5) If plain UDP is blocked on the client path, use Xray instead:
     sudo wg-ops install-xray

EOF
elif [[ "$ok" -eq 0 && "$never" -gt 0 ]]; then
  cat <<EOF

No client traffic reached ${CLIENT_IF} yet (or peers unused).

1) Import a current .conf and activate the tunnel on a device.
2) Cloud/provider firewall: allow inbound UDP ${client_port} to this entry.
3) Host firewall: sudo wg-ops open-ports --role entry
4) tcpdump while connecting:
     sudo tcpdump -ni ${WAN_IF} udp port ${client_port} -c 20

EOF
elif [[ "$ok" -gt 0 ]]; then
  log "At least one client handshake is present — client path OK for those peers."
fi

echo
wg show "$CLIENT_IF"
