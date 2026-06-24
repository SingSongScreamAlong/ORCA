# ORCA appliance — git-over-VPN deploy

The sealed-appliance deploy model: develop and push from your dev machine, and the VM
runs **one script** that resets to the pushed commit and rebuilds. The appliance only
ever pulls *released source* and rebuilds from it — nothing is hand-edited on the box,
so its running state is always reproducible from a single git commit. For a tool that
handles case evidence, that reproducibility is the audit story.

```text
  dev machine  ──push──▶  GitHub (origin/main)  ──pull over VPN──▶  VM appliance
   (edit, verify green,        source of truth         (~/orca-update.sh:
    commit, push)                                       reset --hard + rebuild)
```

## Steady-state loop (every cycle)

1. **Dev machine** — edit, verify green, commit, push:
   ```bash
   cd backend && ruff check . && python -m pytest -q          # backend green
   cd ../frontend && npm run typecheck && npm run build       # frontend green
   git add -A && git commit -m "…" && git push origin main
   ```
2. **GitHub** — `origin/main` holds the source of truth.
3. **VM** — pull + rebuild:
   ```bash
   ~/orca-update.sh
   ```
   That runs `git fetch` + `git reset --hard origin/main`, reinstalls backend deps,
   rebuilds the frontend, and restarts the services — so the box ends up byte-identical
   to what was pushed. `reset --hard` throws away any local drift, guaranteeing
   "what was tested" == "what runs".

## One-time VM bootstrap

### 1. A read-only deploy key (not your login)

So the appliance is **not tied to your GitHub identity**: generate a per-repo SSH key
that lives only on the VM. It is the *repo's* read credential, revocable any time — not
your account.

```bash
ssh-keygen -t ed25519 -C "orca-appliance" -f ~/.ssh/orca_deploy -N ""
cat ~/.ssh/orca_deploy.pub      # → add in GitHub: repo ▸ Settings ▸ Deploy keys
                                #   (read-only; do NOT check "allow write access")
# tell git/ssh to use this key for the repo host
cat >> ~/.ssh/config <<'EOF'
Host github.com-orca
  HostName github.com
  User git
  IdentityFile ~/.ssh/orca_deploy
  IdentitiesOnly yes
EOF
```

The VM reaches GitHub **out through the VPN** (the same egress lock everything else
uses) — that's the "over-VPN" part. The deploy key authenticates the *box*, not you.

### 2. Clone once

```bash
git clone git@github.com-orca:SingSongScreamAlong/ORCA.git ~/ORCA
cd ~/ORCA
```

### 3. First build

```bash
scripts/appliance/orca-update.sh        # builds backend venv + frontend, no services yet
```

### 4. Install the services (systemd --user) + a launcher

```bash
mkdir -p ~/.config/systemd/user
cp scripts/appliance/orca-backend.service  ~/.config/systemd/user/
cp scripts/appliance/orca-frontend.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now orca-backend.service orca-frontend.service

# keep user services running after logout / across reboots
loginctl enable-linger "$USER"

# so you can just type the update from anywhere
ln -sf ~/ORCA/scripts/appliance/orca-update.sh ~/orca-update.sh
```

That's it. From then on the whole deploy is: **push on the dev machine → `~/orca-update.sh`
on the VM.**

## Notes

- **Storage.** Defaults to the in-memory store (no DB) — fine for evaluation, but state
  resets on restart. For durable evidence, set `ORCA_STORAGE_BACKEND=postgres` and the
  DSN in `~/ORCA/backend/.env`; the update script then runs `alembic upgrade head` each
  cycle (bring Postgres up with `infrastructure/docker-compose.yml`).
- **Discovery / collection stay off** until you configure a licensed provider
  (`ORCA_HUNTING_DISCOVERY_PROVIDER=…` + lawful basis); dark-web/Tor additionally needs
  `pip install ".[tor]"`, a Tor SOCKS proxy, and `ORCA_HUNTING_DISCOVERY_DARKWEB_ACK=true`.
- **Bind address.** Both services bind `127.0.0.1` — the appliance is not a public server.
  Reach the UI at `http://127.0.0.1:3000` on the box, or tunnel in.
- **Branch.** Tracks `origin/main` by default; override per run with `ORCA_BRANCH=…`.
