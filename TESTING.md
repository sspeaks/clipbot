# Pogbot Testing Checklist

This document covers how to systematically test all changes introduced in this update:
the multi-file refactor, bug fixes, and the new "clip that" feature.

## Prerequisites

- A Discord server with a `poggers` text channel
- Pogbot's Discord token and API keys configured
- At least one audio file in `assets/audio/`
- A voice channel you can join
- `ffmpeg` available on PATH

### Build & Deploy

```bash
# Local (nix-build)
nix build .#default

# Or if testing on your NixOS host, rebuild with pogbot enabled
sudo nixos-rebuild switch
```

Verify the bot starts without errors in the systemd journal:
```bash
journalctl -u pogbot -f
```

---

## Phase 0: Refactor Regression Tests

These verify that the multi-file split didn't break any existing behavior.

### 0.1 — Bot Startup
- [x] Bot connects and prints `CONNECTED!` to logs
- [x] Bot prints `is connected to the following guild:` for your server
- [x] No import errors or tracebacks on startup

### 0.2 — Pog Reaction
- [x] Send any message containing "pog" (e.g. "that was poggers") in any channel
- [x] Bot adds the `:mentos:` reaction to the message
- [x] Bot does **not** react to its own messages

### 0.3 — `!pogcheck`
- [x] Type `!pogcheck` in the `poggers` channel
- [x] Bot responds with a pog rating message and an embedded gif
- [x] Rating is between 1-10; low/medium/high messages match the value

### 0.4 — `!pogmedaddy`
- [x] Join a voice channel
- [x] Type `!pogmedaddy` in the `poggers` channel
- [x] Bot joins, plays a random clip with randomized speed/pitch, then disconnects
- [x] The command message is deleted after playback
- [x] If you're **not** in a voice channel, bot DMs you an error

### 0.5 — `!bettermage`
- [x] Type `!bettermage` in the `poggers` channel
- [x] Bot responds with a mage message, the `nolorra_better.png` image, and plays `AndHisNameIs.mp3`
- [x] Bot does **not** trigger `!bettermage` from its own messages

### 0.6 — `!help`
- [x] Type `!help` in the `poggers` channel
- [x] Bot responds with a code block listing all commands
- [x] New commands `!listen`, `!leave`, and "clip that" are documented

### 0.7 — `!tokens`
- [x] Type `!tokens` in the `poggers` channel
- [x] Bot responds with your token count

### 0.8 — `!playclip`
- [x] Type `!playclip pogmedaddy.mp3` in `poggers` (while in a voice channel)
- [x] Bot joins, plays the file unmodified, deducts a token, confirms
- [x] Type `!playclip nonexistent.mp3` — bot responds with error message
- [x] Type `!playclip` (no filename) — bot tells you the correct syntax

### 0.9 — `!files`
- [x] Send `!files` as a **DM to pogbot** (not in a channel)
- [x] Bot responds with a header message and a list of audio filenames sorted by date
- [x] Typing `!files` in a server channel does **not** trigger the command

### 0.10 — `!chat`
- [x] Type `!chat what is 2+2` in the `poggers` channel
- [x] Bot responds with an AI-generated answer (should include "4")
- [x] Long responses are split into multiple messages (under 2000 chars each)

### 0.11 — `!image`
- [x] Type `!image a cute cat` in **any** channel (not restricted to `poggers`)
- [x] Bot responds with an embedded AI-generated image
- [x] Image is uploaded to Azure Blob Storage

### 0.12 — Channel Restrictions
- [x] Commands like `!pogcheck`, `!chat`, `!tokens` do **nothing** outside `poggers`
- [x] `!image` works in any channel
- [x] `!files` only works in DMs

---

## Phase 1: Listening Infrastructure

### 1.1 — `!listen` (Happy Path)
- [ ] Join a voice channel
- [x] Type `!listen` in `poggers`
- [x] Bot joins your voice channel
- [x] Bot responds: "🎙️ Listening! Say **"clip that"** to save a clip, or type `!leave` to stop."
- [x] Check logs — web server should print `Clip trimmer web server running on http://0.0.0.0:8080`

### 1.2 — `!listen` (Edge Cases)
- [x] Type `!listen` when **not** in a voice channel — bot responds with error
- [x] Type `!listen` when bot is **already** listening — bot responds "Already listening!"

### 1.3 — `!leave`
- [x] Type `!leave` in `poggers` while bot is listening
- [x] Bot disconnects from voice and responds "👋 Stopped listening."
- [x] Type `!leave` when bot is **not** listening — bot responds "Not currently listening"

---

## Phase 2: "Clip That" Detection

### 2.1 — Trigger Detection
- [ ] Have the bot listening (`!listen`)
- [ ] Speak normally for a few seconds, then say **"clip that"** clearly
- [ ] Within ~5-10 seconds, bot posts: "🎬 **Clip captured!** Trim it here: <url>"
- [ ] The URL matches the `POGBOT_TRIMMER_URL` env var pattern

### 2.2 — Alternative Triggers
- [ ] Say **"clip it"** — should also trigger
- [ ] Say **"save that"** — should also trigger

### 2.3 — Cooldown
- [ ] Say "clip that" twice within 10 seconds
- [ ] Only **one** clip should be captured (second is ignored during cooldown)

### 2.4 — No False Positives
- [ ] Have a normal conversation without saying trigger phrases
- [ ] No clips should be captured
- [ ] Check logs for any Whisper transcription errors

---

## Phase 3: Web Trimmer

### 3.1 — Trimmer Page Loads
- [ ] Click the trim URL from the Discord message
- [ ] Page loads with the title "🎬 Trim Your Clip"
- [ ] Waveform renders showing the audio data
- [ ] Selection defaults to full clip duration

### 3.2 — Waveform Interaction
- [ ] Click and drag on the waveform to select a region
- [ ] The blue selection overlay updates in real-time
- [ ] The "Selected: Xs - Ys (Zs)" text updates
- [ ] Start/End number inputs update to match the selection

### 3.3 — Manual Time Input
- [ ] Change the Start input to `5.0` — selection updates
- [ ] Change the End input to `15.0` — selection updates
- [ ] Start cannot exceed End, End cannot exceed duration

### 3.4 — Preview Playback
- [ ] Click "▶ Preview" — only the selected range plays through your speakers
- [ ] Click Preview again — previous playback stops, new one starts

### 3.5 — Save Clip
- [ ] Enter a clip name (e.g. `my-cool-clip`)
- [ ] Click "💾 Save to Clip Store"
- [ ] Button changes to "Saving..." then "Saved!"
- [ ] Success message: `✅ Saved as "my-cool-clip.mp3"! You can close this page.`
- [ ] In Discord, bot posts: `✅ New clip **my-cool-clip.mp3** saved! Play it with !playclip my-cool-clip.mp3`

### 3.6 — Saved Clip Playback
- [ ] Type `!playclip my-cool-clip.mp3` in `poggers`
- [ ] The trimmed clip plays correctly in voice
- [ ] The clip shows up in `!files` (via DM)

### 3.7 — Error Cases
- [ ] Try saving with an empty clip name — error shown
- [ ] Try saving with a selection < 0.5s — error shown
- [ ] Try saving with a name that already exists — error: "A clip with that name already exists"
- [ ] Visit `/trim/nonexistent` — 404 page
- [ ] Visit `/audio/nonexistent` — 404 response

### 3.8 — Filename Sanitization
- [ ] Enter a name with special chars: `my clip!@#$` → saved as `my clip.mp3` (only alphanumeric, `-`, `_`, space kept)
- [ ] `.mp3` extension is appended automatically if missing

---

## Phase 4: Temp File Cleanup

### 4.1 — Cleanup Task
- [ ] Trigger a clip with "clip that" but do **not** trim/save it
- [ ] Verify the temp `.wav` file exists in `{assets_path}/temp_clips/`
- [ ] Wait >1 hour (or temporarily change `interval_seconds` and the 3600 threshold for testing)
- [ ] Verify the temp file is deleted and the pending clip entry is removed

---

## Phase 5: Nix Packaging

### 5.1 — Build
- [ ] `nix build .#default` completes without errors
- [ ] Output contains `$out/lib/pogbot/` directory with all `.py` files
- [ ] Output contains `$out/bin/pogbot` wrapper script
- [ ] `trimmer.html` is included in the output

### 5.2 — NixOS Module Options
- [ ] `services.pogbot.webPort` defaults to `8080`
- [ ] `services.pogbot.trimmerUrl` defaults to `http://localhost:8080`
- [ ] Setting `services.pogbot.trimmerUrl = "https://mycatsonfire.com/pogbot"` passes through to `POGBOT_TRIMMER_URL` env var
- [ ] Firewall opens the configured web port

### 5.3 — Dependency Check
- [ ] `discord-ext-voice-recv` is available to the Python environment
- [ ] `import discord.ext.voice_recv` works inside the Nix build

---

## Quick Smoke Test (5 minutes)

If you just want a fast sanity check before deploying:

1. `nix build .#default` — does it build?
2. Start the bot — does it connect without import errors?
3. `!help` — do all commands show up?
4. `!pogcheck` — does it respond?
5. `!listen` (while in voice) — does it join and print the listening message?
6. Say "clip that" — does a trim URL appear?
7. Open the URL — does the waveform load?
8. `!leave` — does it disconnect cleanly?

---

## Deployment Guide

Pogbot runs on the Azure NixOS server. The clip trimmer web UI is reverse-proxied
through Caddy on the mycatsonfire.com server.

```
┌──────────────────────┐       HTTPS        ┌──────────────────────────┐
│  User's browser      │ ─────────────────→ │  mycatsonfire.com        │
│                      │                    │  (Caddy)                 │
└──────────────────────┘                    │                          │
                                            │  /pogbot/* ──→ reverse   │
                                            │    proxy to Azure:8080   │
                                            └────────────┬─────────────┘
                                                         │ HTTP :8080
                                                         ▼
                                            ┌──────────────────────────┐
                                            │  nixos-azure             │
                                            │  (pogbot + web server)   │
                                            │  Port 8080 open          │
                                            └──────────────────────────┘
```

### Server 1: nixos-azure (pogbot)

Update your existing pogbot NixOS config at `nixos-config/hosts/nixos-azure/pogbot.nix`:

```nix
{ inputs, config, ... }:
let
  sopsFileLocation = {
    format = "yaml";
    sopsFile = ../../secrets/nixos-azure.yaml;
  };
in
{
  imports = [
    inputs.pogbot.nixosModules.default
  ];

  sops.secrets = {
    ASSETS_PATH = sopsFileLocation;
    DISCORD_TOKEN = sopsFileLocation;
    GIPHY_API_KEY = sopsFileLocation;
    OPEN_AI_KEY = sopsFileLocation;
  };

  services.pogbot = {
    enable = true;
    assetsPathFile = config.sops.secrets.ASSETS_PATH.path;
    discordTokenFile = config.sops.secrets.DISCORD_TOKEN.path;
    giphyAPIKeyFile = config.sops.secrets.GIPHY_API_KEY.path;
    openAIAPIKeyFile = config.sops.secrets.OPEN_AI_KEY.path;

    # NEW: clip trimmer settings
    webPort = 8080;
    trimmerUrl = "https://mycatsonfire.com/pogbot";
  };
}
```

After rebuilding (`sudo nixos-rebuild switch`), verify:

```bash
# Bot is running
systemctl status pogbot

# Web server is listening
curl -s http://localhost:8080/trim/test | head -1
# Should return: "Clip not found or expired."

# Firewall port is open
sudo nft list ruleset | grep 8080
```

### Server 2: mycatsonfire.com (Caddy)

Add a reverse proxy block to your Caddyfile. The key detail is that
`/pogbot/` on the public URL maps to `/` on pogbot's web server,
so we need to strip the `/pogbot` prefix.

```caddyfile
mycatsonfire.com {
    # ... your existing site config ...

    handle_path /pogbot/* {
        reverse_proxy <AZURE_PUBLIC_IP>:8080
    }
}
```

`handle_path` automatically strips the matched prefix (`/pogbot`) before
forwarding, so `https://mycatsonfire.com/pogbot/trim/abc123` becomes
`http://<AZURE_IP>:8080/trim/abc123` — exactly what pogbot's web server expects.

After editing, reload Caddy:

```bash
sudo systemctl reload caddy
# or: caddy reload --config /path/to/Caddyfile
```

Verify the proxy works:

```bash
# From anywhere on the internet:
curl -s https://mycatsonfire.com/pogbot/trim/test
# Should return: "Clip not found or expired."
```

### Security Considerations

The pogbot web server on port 8080 is currently open to anyone who knows the
Azure server's public IP. To lock it down so only Caddy can reach it:

**Option A: Firewall restrict to Caddy's IP**

In your `nixos-azure` NixOS config, replace the blanket firewall open with
an nftables rule that only allows the Caddy server:

```nix
# Instead of the auto-generated:
#   networking.firewall.allowedTCPPorts = [ 8080 ];
# Use a more specific rule:
networking.nftables.rules = ''
  # Only allow Caddy server to reach pogbot web UI
  ip saddr <CADDY_SERVER_IP> tcp dport 8080 accept
'';
```

To do this, you'd set `webPort` but also manually manage the firewall
instead of relying on the auto-opened port in `pogbot.nix`.

**Option B: Bind to localhost + SSH tunnel (most secure)**

Change pogbot to only listen on localhost, and use an SSH tunnel from
the Caddy server:

On nixos-azure, bind to localhost only (requires a small code change to
`server.py` — change `0.0.0.0` to `127.0.0.1`). Then from the Caddy server:

```bash
# Persistent SSH tunnel (run as a service)
ssh -N -L 8080:127.0.0.1:8080 user@<AZURE_IP>
```

And point Caddy at `localhost:8080` instead of the Azure IP.

**Option C: Accept the risk (simplest)**

Port 8080 serves a simple trimmer page. The worst someone can do is view/trim
a clip if they guess the 8-character UUID. No auth, no secrets exposed. If
you're okay with that, the default config works as-is.
