# exe.dev gotchas observed during this benchmark

## VM tier limits (free / default plan)

- `--cpu` is capped at **2**. Trying to create with `--cpu=4` returns:
  `--cpu cannot exceed 2 — run \`billing update\` to upgrade to a larger plan`.
- `--memory=4GB` works at the default tier; 3.8 GiB RAM available, no swap.
- 30 GB disk: fine.
- The benchmark therefore ran on the entry tier: **2 vCPU / 4 GB RAM**.

## Provisioning

```fish
ssh exe.dev new --name=myvm --cpu=2 --memory=4GB --disk=30GB --json
```

Returns immediately with `ssh_dest`, `https_url` (port 8000 by default), `vscode_url`, etc.
First SSH connection prompts host key — use `-o StrictHostKeyChecking=accept-new` for non-interactive.

## Image / OS

- Default image is Ubuntu-ish (`Linux 6.12.87 SMP x86_64`).
- `apt-get` works out of the box; user is `exedev` with sudo.
- ffmpeg / build-essential / cmake install cleanly.

## Public URLs

- HTTPS at `https://<vm>.exe.xyz/` proxied to **port 8000** by default
  (configurable via `ssh exe.dev share port`).
- Phase B WebSocket testing — not run in v1; deferred.

## Phase B smoke-tests (deferred until streaming POC is built)

- [ ] WebSocket upgrade through `<vm>.exe.xyz`
- [ ] 10-minute idle WS hold
- [ ] No reverse-proxy buffering of streamed responses
