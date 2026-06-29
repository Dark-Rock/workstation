# Terminal command discovery

This workstation ships a large modern CLI toolset (see [`TOOLS.md`](../TOOLS.md)).
This guide answers *"I want to do X — what do I run?"* and documents the layers
that make commands discoverable without memorizing every binary in `packages.toml`.

## The three discovery entry points

Fastest first:

| Entry point | How | When |
| --- | --- | --- |
| **`Ctrl-G`** (navi) | Fuzzy-search curated "intent → command" cheats; pick one and it lands on your command line with placeholders to fill. Never auto-runs. | Curated, workstation-specific recipes. Offline + instant. |
| **`howto "..."`** | Plain-English request → a single command via the local `claude` CLI, placed on the line for review. | Free-form questions the cheats don't cover. Needs network. |
| **Smart fallbacks** | A few short commands open an fzf picker when run with **no arguments**. | In-flow, no thinking required. |

Plus the always-on general-purpose layers (history, examples, completions) below.

### `Ctrl-G` — navi cheats

Press `Ctrl-G` (or run `navi`). Type intent — "find large files", "tail pod
logs", "scan image" — choose an entry, and navi fills the command in for editing.

Ctrl-G is populated from **two** sources (both configured in
[`navi/config.yaml`](../dotfiles/config/.config/navi/config.yaml)):

1. **Curated workstation cheats** —
   [`dotfiles/config/.config/navi/cheats/`](../dotfiles/config/.config/navi/cheats/),
   the modern-tool recipes that are the source of the task reference below.
2. **Community cheats** — the [`denisidoro/cheats`](https://github.com/denisidoro/cheats)
   repo (hundreds of default-command recipes: git, docker, kubectl, tar, gpg,
   ssh, networking, …). `wkst` clones it into navi's data dir on `wkst install`
   and refreshes it on `wkst update`, so it is reproducible on any machine.

Need something neither covers? Pull from the wider ecosystem on the fly:

```bash
navi --tldr docker      # browse tldr-pages entries for a topic
navi --cheatsh tar      # browse cheat.sh entries for a topic
```

### `howto` — natural language → command

```bash
howto find files over 100MB changed in the last day
howto port-forward the postgres service on 5432
howto show the 10 biggest directories here
```

`howto` (defined in [`.zshrc`](../dotfiles/zsh/.zshrc)) asks the local `claude`
CLI to translate the request into one command, preferring the modern tools
installed here, and places it on the command line **for review** — you press
Enter. It never executes on its own.

### Smart fallbacks

A short command with **no arguments** opens a fuzzy picker; with arguments it
behaves normally. Guarded to interactive shells, so scripts are unaffected.

| Command | No args | With args |
| --- | --- | --- |
| `gco` | fuzzy branch switcher (commit-log preview) | `git checkout <args>` |

The shell also ships fzf-powered helpers: `gbr` (branches), `gfzf` (commits),
`fkill` (processes), `fv` (find+edit), `fcd` (find+cd), `ksh` (pod shell),
`klf` (pod logs), `kctx` (context), `kpff` (port-forward), `dsh` (container shell).

### General-purpose layers (always on)

| Intent | Command / key | What it gives you |
| --- | --- | --- |
| Quick examples for a tool | `tldr <topic>` | Curated practical examples (tealdeer). |
| More examples from the web | `cheat <topic>` | `cheat.sh` via the `.zshrc` function. |
| "I ran this before" | `Ctrl-r` / `Alt-Up` | Atuin history search. |
| "I typed it wrong" | `f` | pay-respects corrects the last command. |
| "I forgot an alias" | type the long command | zsh-you-should-use reminds you. |
| Completions + previews | `Tab` | zsh completions, fzf-tab menus, bat/eza previews. |
| Pick a file / dir | `Ctrl-t` / `Alt-c` | fzf file/dir pickers. |

---

## Task reference

Modern tool first; the legacy command it replaces in parentheses.

### Files & search

| I want to… | Command |
| --- | --- |
| Find files by name | `fd <pattern>` (find) |
| Find hidden/ignored too | `fd --hidden --no-ignore <pattern>` |
| Find files over a size | `fd --type f --size +100m` |
| Search file contents | `rg <query>` (grep) |
| Project-wide search & replace | `grug-far` (in nvim) |
| Browse files in a TUI | `yazi` |
| View/navigate JSON | `jless <file>` |
| Query JSON/YAML/TOML/CSV | `dasel -f <file> '<selector>'` |
| Query/transform JSON · YAML | `jq '<filter>'` · `yq` |
| View a file (highlighted) | `bat <file>` · `show` (cat) |
| List files | `ls`/`ll`/`lt` → eza (ls) |
| Disk usage, biggest first | `dust` (du) |
| Free space per filesystem | `duf` (df) |
| Hex dump | `hexyl <file>` |
| Count lines by language | `tokei` |
| Syntax-aware code search | `ast-grep --pattern '<pat>'` |
| Jump to a known dir | `z <name>` · pick `zi` (cd) |

### Git

| I want to… | Command |
| --- | --- |
| Interactive git UI | `lazygit` (`lg`) |
| Lightweight git UI | `gitui` |
| Compact status | `gs` |
| Syntax-aware diff | `difft <a> <b>` |
| Pretty pager diffs | `git diff` (delta, themed) |
| Switch branch (fuzzy) | `gco` (no args) · `gbr` |
| Browse/show a commit | `gfzf` |
| Review a big change | `nvim -c DiffviewOpen` |
| Create a PR | `gh pr create --web` |

### Kubernetes (read-only first)

| I want to… | Command |
| --- | --- |
| Cluster TUI | `k9s` |
| Explain what's broken (AI) | `k8sgpt analyze --explain` |
| Switch context / namespace | `kubectx` / `kubens` (`kx`/`kns`) |
| Get pods | `kgp` / `kgpw` / `kgpa` |
| Follow logs | `klog <pod>` / `klf` |
| Tail logs across pods | `stern <selector>` |
| Capture cluster traffic | `kubeshark tap` |
| Scan cluster health | `popeye` |
| Lint a manifest | `kube-linter lint <path>` |
| Validate manifest schema | `kubeconform -summary <file>` |
| Preview an apply | `kubectl diff -f <file>` |
| Shell into a pod (fuzzy) | `ksh` |

Avoid destructive aliases (`kdel`, `krollr`, `kscale`) until you've confirmed
context, namespace, and blast radius.

### Containers

| I want to… | Command |
| --- | --- |
| Docker TUI | `lazydocker` |
| Running containers | `dps` |
| Shell into a container | `dsh` / `dex <c>` |
| Inspect image layers | `dive <image>` |
| Scan image for CVEs | `trivy image <image>` |

### System & processes

| I want to… | Command |
| --- | --- |
| Live system monitor | `btop` / `btm` (top) |
| Process list | `procs <filter>` (ps) |
| Per-process bandwidth | `sudo bandwhich` |
| Ping with a graph | `gping <host>` |
| Traceroute TUI | `sudo trip <host>` |
| Benchmark a command | `hyperfine '<cmd>'` |
| Explore logs | `lnav <logfile>` |
| Listening ports | `listening` |
| Kill a process (fuzzy) | `fkill` |

### Network & API

| I want to… | Command |
| --- | --- |
| HTTP request | `xh <method> <url>` (curl) |
| HTTP tests from a file | `hurl --test <file.hurl>` |
| DNS lookup | `doggo <domain>` (dig) |
| Network scan | `nmap <target>` |
| gRPC call | `grpcurl -plaintext <host:port> list` |
| gRPC in a browser | `grpcui ...` |
| WebSocket client | `websocat <url>` |
| Quick load test | `oha -z 30s <url>` |
| Scripted load test | `k6 run <script.js>` |

### Data & databases

| I want to… | Command |
| --- | --- |
| SQL over CSV/JSON/Parquet | `duckdb -c "SELECT … FROM '<file>'"` |
| Postgres REPL | `pgcli <conn>` |
| MySQL/MariaDB REPL | `mycli <conn>` |
| Terminal SQL IDE | `harlequin <conn>` |

### Security & secrets

| I want to… | Command |
| --- | --- |
| Scan repo for secrets | `gitleaks detect` |
| Verify leaked credentials | `trufflehog filesystem <path>` |
| Generate an SBOM | `syft <image>` |
| Scan for vulnerabilities | `grype <image>` |
| Verify image signature | `cosign verify <image>` |
| Edit encrypted secrets | `sops <file>` |

### Quality & formatting

| I want to… | Command |
| --- | --- |
| Python lint + format | `ruff check` · `ruff format` |
| Python types | `mypy` · `pyright` |
| Shell lint / format | `shellcheck` · `shfmt` |
| TOML lint / format | `taplo check` · `taplo fmt` |
| YAML / Markdown lint | `yamllint` · `markdownlint-cli2` |
| GitHub Actions lint | `actionlint` |
| Run repo hooks | `pre-commit run --all-files` |

### Documents

| I want to… | Command |
| --- | --- |
| Convert documents | `pandoc ...` |
| Render Mermaid diagrams | `mmdc ...` |
| Image / PDF manipulation | `magick` · `gs` |

---

## Default-command replacement layer

The zsh config aliases a few defaults to richer tools. They are still aliases —
use `command <name>` (e.g. `command ls`) to bypass one when needed.

| Default | Workstation alias | Notes |
| --- | --- | --- |
| `ls` | `eza --icons --group-directories-first` | `la`, `l`, `ll`, `lt` give common views. |
| `tree` | `eza --icons -T` | Familiar name, better output. |
| `grep` | `rg` | Faster recursive search. |
| `top` | `btop` | Better interactive monitor. |
| `cd` | `z` / `zi` (zoxide) | Frecency jumps; `cd` itself is unchanged. |
| `rm`/`cp`/`mv` | `rm -I` / `cp -iv` / `mv -iv` | Safer, verbose. |

Note: `cat` and `less` are intentionally **not** aliased to `bat` (that breaks
scripts and here-docs) — use `bat`, `show`, or `b` explicitly.

---

## Extending

- **Add a curated cheat:** append to `navi/cheats/workstation.cheat`
  (`# description` line, then the command; use `<placeholders>` and
  `$ name: <source cmd>` for fuzzy-filled args). New files need `wkst sync`. It
  shows up under `Ctrl-G` immediately — add it to the task reference above too.
- **Add another community cheat repo:** clone it into navi's data dir
  (`~/.local/share/navi/cheats/<user>__<repo>`), or wire it like
  `denisidoro/cheats` in `_ensure_navi_cheats` in
  [`wkst/plugins.py`](../wkst/plugins.py) for reproducible installs. Run
  `navi repo browse` to discover featured repos.
- **Tune `howto`:** edit the tool list / prompt in the `howto()` function in
  [`.zshrc`](../dotfiles/zsh/.zshrc).

## Maintenance

- `packages.toml` is the source of truth for installed tools; keep each tool's
  `description` current.
- `TOOLS.md` is generated from it via `just docs`.
- Update this guide when a change affects day-to-day terminal workflows.
