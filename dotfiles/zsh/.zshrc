# ==================================================
# LOCAL SECRETS (git-ignored, machine-local)
# ==================================================
# Credentials and machine-specific exports live here, NEVER in the tracked
# dotfiles. Create ~/.config/zsh/.secrets.zsh and export secrets there, e.g.:
#   export CRITEO_PASSWORD="..."   # or source from Vault
[ -f "${HOME}/.config/zsh/.secrets.zsh" ] && source "${HOME}/.config/zsh/.secrets.zsh"

# ==================================================
# ZINIT BOOTSTRAP
# ==================================================
# Skip cloning if folder exists
if [ -f "${HOME}/.zinit/bin/zinit.zsh" ]; then
    source "${HOME}/.zinit/bin/zinit.zsh"
else
    mkdir -p "${HOME}/.zinit"
    git clone https://github.com/zdharma-continuum/zinit.git "${HOME}/.zinit/bin"
    source "${HOME}/.zinit/bin/zinit.zsh"
fi

# ==================================================
# OPTIONS
# ==================================================
setopt AUTOCD
setopt PROMPTSUBST
setopt MENU_COMPLETE
setopt AUTO_LIST
setopt COMPLETE_IN_WORD
setopt EXTENDED_GLOB
setopt HIST_IGNORE_ALL_DUPS
setopt SHARE_HISTORY
setopt INC_APPEND_HISTORY
setopt HIST_FIND_NO_DUPS
setopt HIST_REDUCE_BLANKS
setopt HIST_VERIFY

# Disable terminal beep
unsetopt BEEP

# ==================================================
# PATHS (safe + ordered)
# ==================================================
typeset -U PATH path

export PATH="$HOME/.cargo/bin:$PATH"
export PATH="$HOME/.go/bin:$PATH"
export PATH="$HOME/.dotnet/tools:$PATH"
if [[ -d "${HOME}/.local/bin" ]]; then
  export PATH="${HOME}/.local/bin:$PATH"
fi

export NPM_GLOBAL="$HOME/.npm-global"
export PATH="$NPM_GLOBAL/bin:$PATH"

# kubectl krew plugins live here when installed.
if [[ -d "${HOME}/.krew/bin" ]]; then
  export PATH="${HOME}/.krew/bin:$PATH"
fi

# Claude Code ECC plugin hooks
export CLAUDE_PLUGIN_ROOT="$HOME/.claude"

# Java (Homebrew OpenJDK)
export JAVA_HOME="/opt/homebrew/opt/java/libexec/openjdk.jdk/Contents/Home"
export PATH="/opt/homebrew/opt/java/bin:$PATH"

# ==================================================
# HISTORY
# ==================================================
export HISTFILE=~/.config/zsh/.zsh_history
export HISTSIZE=50000
export SAVEHIST=$HISTSIZE

# ==================================================
# ZINIT PLUGINS
# ==================================================

# Evalcache stays synchronous: every _evalcache call below depends on it.
zinit light mroth/evalcache

# --- Deferred (turbo) plugin loading ---------------------------------------
# Everything below loads just after the first prompt paints (`wait lucid`), so
# it is off the startup critical path. Plugin *settings* are set here (they are
# read when the plugin actually loads). Ordering matters: zsh-completions is
# queued before the group that runs compinit, and fzf-tab loads after it.

# Version-pinned completion dump (replaces the old manual compinit block). The
# single `zicompinit` below honours this path.
ZINIT[ZCOMPDUMP_PATH]="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompdump-${ZSH_VERSION}"
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/zsh"

# Autosuggestion styling (read when the plugin loads below).
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=240'
ZSH_AUTOSUGGEST_STRATEGY=(completion)
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE=20

# You-should-use settings.
export YSU_MESSAGE_POSITION="after"
export YSU_MODE=ALL
# export YSU_HARDCORE=1

# Completion definitions — blockf keeps them off fpath until compinit runs.
zinit ice wait lucid blockf
zinit light zsh-users/zsh-completions

# Autosuggestions, autopair, and syntax highlighting. fast-syntax-highlighting
# loads LAST and carries the single, cached (`-C`) compinit call. By the time it
# fires (first prompt) the brew fpath additions below have already run, and
# zsh-completions is queued, so compinit sees every completion. Immediately
# after compinit we load all tool completions (kubectl, helm, gh, …) — they call
# `compdef`, so they MUST run after compinit (see _wkst_load_tool_completions).
zinit wait lucid for \
  atload"!_zsh_autosuggest_start" \
    zsh-users/zsh-autosuggestions \
  hlissner/zsh-autopair \
  atinit"ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay; _wkst_load_tool_completions" \
    zdharma-continuum/fast-syntax-highlighting

# fzf-tab must load AFTER compinit (above). fzf itself is integrated via
# `eval "$(fzf --zsh)"` below, not as a zinit plugin — avoids cloning the fzf
# repo and double-loading its bindings.
zinit ice wait lucid
zinit light Aloxaf/fzf-tab

# Lower-priority extras (history-search-multi-word removed: it bound Ctrl-R but
# Atuin rebinds Ctrl-R afterward, so it was fully shadowed — see ATUIN section).
zinit wait lucid for \
  MichaelAquilina/zsh-you-should-use \
  OMZP::colored-man-pages \
  OMZP::sudo

# ==================================================
# OH-MY-POSH PROMPT (REPLACES POWERLEVEL10K)
# ==================================================
eval "$(oh-my-posh init zsh --config "${HOME}/.config/oh-my-posh/base.json")"

# ==================================================
# COMPLETIONS (brew extras)
# ==================================================
if command -v brew >/dev/null; then
  BREW_PREFIX="$(brew --prefix)"
  if [[ -d "${BREW_PREFIX}/share/zsh-completions" ]]; then
    fpath+=("${BREW_PREFIX}/share/zsh-completions")
  fi
fi

# Package upgrades are now driven by `wkst update` (run on demand or via cron).
# The old `_auto_brew_upgrade` background hook was removed to keep shell startup
# fast and predictable; see https://github.com/<user>/config-workstation/wkst.

# LS colors are also used by completion styling below.
if command -v vivid >/dev/null; then
  export LS_COLORS="$(vivid generate catppuccin-macchiato)"
fi

# compinit is run exactly once, deferred, by the turbo block above
# (`zicompinit`, cached via -C, dumping to ZINIT[ZCOMPDUMP_PATH]). The previous
# explicit compinit here was a second, redundant invocation — removed.

# Better completion menu styling
zstyle ':completion:*' menu select
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*:descriptions' format '%F{yellow}-- %d --%f'
zstyle ':completion:*:warnings' format '%F{red}-- No matches found --%f'
zstyle ':completion:*:messages' format '%F{purple}-- %d --%f'
zstyle ':completion:*:corrections' format '%F{yellow}-- %d (errors: %e) --%f'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' verbose yes
zstyle ':completion:*:manuals' separate-sections true
zstyle ':completion:*:manuals.*' insert-sections true
zstyle ':completion:*' matcher-list \
  'm:{[:lower:][:upper:]}={[:upper:][:lower:]}' \
  'l:|=* r:|=*'

# Color completion for kill command
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'

# ==================================================
# FZF
# ==================================================
# Modern integration (fzf >= 0.48): generates keybindings + completion.
# Falls back to the legacy ~/.fzf.zsh if present (older fzf).
if command -v fzf >/dev/null; then
  eval "$(fzf --zsh)"
elif [ -f "$HOME/.fzf.zsh" ]; then
  source "$HOME/.fzf.zsh"
fi

# ==================================================
# FZF CONFIGURATION
# ==================================================
export FZF_DEFAULT_OPTS="
  --height 40%
  --layout=reverse
  --border
  --preview-window=right:60%
  --color=bg+:#363a4f,bg:#24273a,spinner:#f4dbd6,hl:#ed8796
  --color=fg:#cad3f5,header:#ed8796,info:#c6a0f6,pointer:#f4dbd6
  --color=marker:#b7bdf8,fg+:#cad3f5,prompt:#c6a0f6,hl+:#ed8796
  --color=selected-bg:#494d64,border:#6e738d,label:#cad3f5
  --bind='ctrl-/:toggle-preview'
  --bind='ctrl-u:preview-half-page-up'
  --bind='ctrl-d:preview-half-page-down'
"
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_CTRL_T_COMMAND="${FZF_DEFAULT_COMMAND}"
export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'

# fzf-tab behavior tweaks
zstyle ':fzf-tab:*' switch-group ',' '.'
zstyle ':fzf-tab:*' fzf-flags '--height=50%' '--preview-window=right:60%'
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always --icons $realpath'
zstyle ':fzf-tab:complete:*:*' fzf-preview 'bat --color=always --style=numbers --line-range :500 $realpath 2>/dev/null || eza -1 --color=always --icons $realpath 2>/dev/null'

# ==================================================
# VI MODE (enable first)
# ==================================================
bindkey -v

# Reduce ESC delay (faster mode switching)
export KEYTIMEOUT=1

# ==================================================
# KEYBINDINGS
# ==================================================
# Alt+arrows for word movement (works in both modes)
bindkey '^[[1;3D' backward-word   # alt-left
bindkey '^[[1;3C' forward-word   # alt-right

# Better completion menu navigation (vim-like)
zmodload zsh/complist
bindkey -M menuselect 'h' vi-backward-char
bindkey -M menuselect 'k' vi-up-line-or-history
bindkey -M menuselect 'l' vi-forward-char
bindkey -M menuselect 'j' vi-down-line-or-history
bindkey -M menuselect '^xi' vi-insert

# Additional useful keybindings
bindkey '^[^?' backward-kill-word  # Alt+Backspace
bindkey '^[[3;5~' kill-word        # Ctrl+Delete
bindkey '^H' backward-kill-word    # Ctrl+Backspace

# ==================================================
# TOOLS
# ==================================================

# zoxide (smart cd) - cached for performance
if command -v zoxide >/dev/null; then
  _evalcache zoxide init zsh
fi

# pay-respects (maintained Rust successor to thefuck) - corrects the last
# command. Provides the `f` alias. Cached for performance.
if command -v pay-respects >/dev/null; then
  _evalcache pay-respects zsh --alias
elif command -v thefuck >/dev/null; then
  _evalcache thefuck --alias
fi

# direnv (auto-load environment variables)
if command -v direnv >/dev/null; then
  _evalcache direnv hook zsh
fi

# atuin (advanced shell history)
if command -v atuin >/dev/null; then
  _evalcache atuin init zsh
fi

# ==================================================
# ALIASES
# ==================================================

# Editor
alias v='nvim'
alias vi='nvim'
alias vim='nvim'
alias edit='nvim'

# Git
alias g='git'
alias gs='git status -sb'
alias gst='git status'
alias gd='git diff'
alias gds='git diff --staged'
alias gc='git commit'
alias gca='git commit --amend'
alias gcn='git commit --no-verify'
alias gp='git push'
alias gpf='git push --force-with-lease'
alias gpl='git pull --rebase'
alias gco='git checkout'
alias gcb='git checkout -b'
alias glog='git log --oneline --graph --decorate --all'
alias glg='git log --graph --pretty=format:"%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset" --abbrev-commit'
alias gundo='git reset --soft HEAD~1'
alias gstash='git stash'
alias gstp='git stash pop'
alias gstl='git stash list'
alias gshow='git show'
alias gclean='git clean -fd'
alias grb='git rebase'
alias grbi='git rebase -i'
alias grbc='git rebase --continue'
alias grba='git rebase --abort'

# Eza (ls replacement) — dirs first, git status in long views
alias ls='eza --icons --group-directories-first'
alias la='eza -a --icons --group-directories-first'
alias l='eza -lah --no-time --icons --group-directories-first --git'
alias ll='eza -laHgh --icons --group-directories-first --git'
alias lt='eza --tree --level=2 --icons --git-ignore'
alias tree='eza --icons -T'

# LazyGit
alias lg='lazygit'

# File operations
alias rm='rm -I'
alias cp='cp -iv'
alias mv='mv -iv'
alias mkdir='mkdir -pv'

# Search
alias ff='fzf'
alias gsearch='rg'
alias grep='rg'

# System
alias path='echo -e ${PATH//:/\\n}'
alias now='date +"%T"'
alias nowdate='date +"%Y-%m-%d"'
alias src='source ~/.zshrc'
# Clear the screen and draw a random shell-color-script.
command -v colorscript >/dev/null && alias cl='clear; colorscript -r'

# Viewers — keep `cat`/`less` as the real tools (aliasing them breaks
# scripts, here-docs, and piping). Use `show`/`b` for bat explicitly.
alias show='bat'
alias b='bat'
alias monitor='btm'
alias top='btop'

# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias ......='cd ../../../../..'
alias ~='cd ~'
alias -- -='cd -'

# Oh-My-Posh
alias omp='oh-my-posh'

# History
alias h='history'
alias hs='history | grep'
alias hsi='history | grep -i'

# ==================================================
# KUBERNETES ALIASES
# ==================================================

# Context and namespace switching
alias kx='kubectx'
alias kns='kubens'
alias krew='kubectl krew'
alias krewls='kubectl krew list'
alias krewsync='kubectl krew update'
alias krewup='kubectl krew upgrade'

# kubectl shortcuts — `k` uses kubecolor (colorized kubectl) when available,
# falling back to plain kubectl. The kgp/kgs/etc. aliases below stay on kubectl
# so they remain pipe-safe and script-friendly.
if command -v kubecolor >/dev/null; then
  alias k='kubecolor'
else
  alias k='kubectl'
fi
alias kgp='kubectl get pods'
alias kgpw='kubectl get pods -o wide'
alias kgpa='kubectl get pods --all-namespaces'
alias kgs='kubectl get svc'
alias kgd='kubectl get deployments'
alias kgn='kubectl get nodes'
alias kgno='kubectl get nodes -o wide'
alias kgi='kubectl get ingress'
alias kga='kubectl get all'
alias kgns='kubectl get namespaces'

# Describe resources
alias kdp='kubectl describe pod'
alias kds='kubectl describe service'
alias kdd='kubectl describe deployment'
alias kdn='kubectl describe node'

# Logs
alias klog='kubectl logs -f'
alias klogs='kubectl logs -f --tail=100'
alias klogp='kubectl logs -f --previous'

# Delete
alias kdel='kubectl delete'
alias kdelp='kubectl delete pod'
alias kdelf='kubectl delete -f'

# Apply/Create
alias kapp='kubectl apply -f'
alias kcre='kubectl create'
alias kdry='kubectl apply --dry-run=client -o yaml'
alias klint='kube-linter lint'

# Execute
alias kex='kubectl exec -it'
alias krun='kubectl run -it --rm --restart=Never'

# Edit
alias ked='kubectl edit'

# Top
alias ktop='kubectl top nodes'
alias ktopp='kubectl top pods'

# Port forward
alias kpf='kubectl port-forward'

# Scale
alias kscale='kubectl scale'

# Rollout
alias kroll='kubectl rollout'
alias krollr='kubectl rollout restart'
alias krolls='kubectl rollout status'
alias krollu='kubectl rollout undo'

# ==================================================
# DOCKER ALIASES
# ==================================================

alias d='docker'
alias dps='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
alias dpsa='docker ps -a'
alias di='docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"'
alias dlog='docker logs -f'
alias dex='docker exec -it'
alias dclean='docker system prune -af'
alias dstop='docker stop $(docker ps -q)'
alias drm='docker rm $(docker ps -aq)'
alias drmi='docker rmi $(docker images -q)'

# Docker Compose
alias dc='docker-compose'
alias dcu='docker-compose up -d'
alias dcd='docker-compose down'
alias dcl='docker-compose logs -f'
alias dcr='docker-compose restart'
alias dcp='docker-compose ps'
alias dcb='docker-compose build'

# ==================================================
# SYSTEM MONITORING ALIASES
# ==================================================

alias ports='netstat -tulanp'
alias listening='lsof -iTCP -sTCP:LISTEN -n -P'
alias meminfo='free -h'
alias psmem='ps auxf | sort -nr -k 4 | head -10'
alias pscpu='ps auxf | sort -nr -k 3 | head -10'
alias disk='df -h'
alias dush='du -sh * | sort -h'

# ==================================================
# QUICK EDITS
# ==================================================

alias zshrc='nvim ~/.zshrc'
alias vimrc='nvim ~/.vimrc'
alias reload='source ~/.zshrc'
alias hosts='sudo nvim /etc/hosts'

# ==================================================
# NETWORK ALIASES
# ==================================================

alias myip='curl -s ifconfig.me'
alias localip='ipconfig getifaddr en0 || hostname -I'
alias pingg='ping 8.8.8.8'
alias speedtest='curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python3 -'

# ==================================================
# GLOBAL ALIASES (work anywhere in command line)
# ==================================================

alias -g G='| grep -i'
alias -g GV='| grep -iv'
alias -g L='| less'
alias -g H='| head'
alias -g T='| tail'
alias -g TF='| tail -f'
alias -g W='| wc -l'
alias -g S='| sort'
alias -g SN='| sort -n'
alias -g N='> /dev/null 2>&1'
alias -g J='| jq .'
alias -g JC='| jq -C . | less -R'
alias -g NE='2> /dev/null'
alias -g NUL='> /dev/null 2>&1'
alias -g Y='| yq .'
alias -g C='| pbcopy'
alias -g X='| xargs'

# ==================================================
# CUSTOM FUNCTIONS
# ==================================================

# Git: Quick commit with message
gcm() {
  git add -A && git commit -m "$*" && git push
}

# Git: Interactive branch switcher with preview
gbr() {
  local branch=$(git branch -a | grep -v HEAD | fzf --preview 'git log --oneline --color=always {1}' | sed 's/^..//' | sed 's/remotes\/origin\///')
  [[ -n "$branch" ]] && git checkout "$branch"
}

# Git: Interactive commit browser
gfzf() {
  git log --oneline --color=always | fzf --ansi --preview 'git show --color=always {1}' | awk '{print $1}' | xargs git show
}

# Docker: Quick container shell access
dsh() {
  local container=$(docker ps --format '{{.Names}}' | fzf --preview 'docker inspect {1}')
  [[ -n "$container" ]] && docker exec -it "$container" sh
}

# Kubernetes: Quick pod shell access
ksh() {
  local pod=$(kubectl get pods --no-headers | fzf --preview 'kubectl describe pod {1}' | awk '{print $1}')
  [[ -n "$pod" ]] && kubectl exec -it "$pod" -- sh
}

# Kubernetes: Quick pod logs with fzf
klf() {
  local pod=$(kubectl get pods --no-headers | fzf --preview 'kubectl logs --tail=50 {1}' | awk '{print $1}')
  [[ -n "$pod" ]] && kubectl logs -f "$pod"
}

# Kubernetes: Switch context with preview
kctx() {
  local context=$(kubectl config get-contexts -o name | fzf --preview 'kubectl config view --context={} --minify')
  [[ -n "$context" ]] && kubectl config use-context "$context"
}

# Kubernetes: Get pod by label selector
kgpl() {
  kubectl get pods -l "$1"
}

# Kubernetes: Port forward with fzf pod selection
kpff() {
  local pod=$(kubectl get pods --no-headers | fzf --preview 'kubectl describe pod {1}' | awk '{print $1}')
  if [[ -n "$pod" ]]; then
    echo "Port forward from $pod"
    read "local_port?Local port: "
    read "remote_port?Remote port: "
    kubectl port-forward "$pod" "${local_port}:${remote_port}"
  fi
}

# Kubernetes: Interactive yaml editor
kedit() {
  local resource=$(kubectl api-resources --verbs=list -o name | fzf)
  [[ -n "$resource" ]] && kubectl edit "$resource"
}

# Find and edit file with preview (uses fd binary explicitly)
fv() {
  local file=$(command fd --type f --hidden --exclude .git | fzf --preview 'bat --color=always --style=numbers {}')
  [[ -n "$file" ]] && nvim "$file"
}

# Find and cd to directory (named fcd to avoid shadowing the fd binary)
fcd() {
  local dir=$(find ${1:-.} -type d 2>/dev/null | fzf --preview 'eza -1 --color=always --icons {}')
  [[ -n "$dir" ]] && cd "$dir"
}

# Create directory and cd into it
mkcd() {
  mkdir -p "$1" && cd "$1"
}

# Extract any archive
extract() {
  if [ -f "$1" ]; then
    case "$1" in
      *.tar.bz2)   tar xjf "$1"    ;;
      *.tar.gz)    tar xzf "$1"    ;;
      *.bz2)       bunzip2 "$1"    ;;
      *.rar)       unrar x "$1"    ;;
      *.gz)        gunzip "$1"     ;;
      *.tar)       tar xf "$1"     ;;
      *.tbz2)      tar xjf "$1"    ;;
      *.tgz)       tar xzf "$1"    ;;
      *.zip)       unzip "$1"      ;;
      *.Z)         uncompress "$1" ;;
      *.7z)        7z x "$1"       ;;
      *)           echo "'$1' cannot be extracted" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

# Quick directory bookmarks
export MARKPATH=$HOME/.marks
jump() {
  cd -P "$MARKPATH/$1" 2>/dev/null || echo "No such mark: $1"
}
mark() {
  mkdir -p "$MARKPATH"
  ln -s "$(pwd)" "$MARKPATH/$1"
}
unmark() {
  rm -i "$MARKPATH/$1"
}
marks() {
  ls -l "$MARKPATH" | sed 's/  / /g' | cut -d' ' -f9- | sed 's/ -/\t-/g' && echo
}

# Weather
weather() {
  curl -s "wttr.in/${1:-}" | head -n -3
}

# Cheat sheet
cheat() {
  curl -s "cheat.sh/$1"
}

# Quick server
serve() {
  python3 -m http.server "${1:-8000}"
}

# Process killer with fzf
fkill() {
  local pid=$(ps -ef | sed 1d | fzf -m | awk '{print $2}')
  if [ "x$pid" != "x" ]; then
    echo $pid | xargs kill -${1:-9}
  fi
}

# Git worktree helper
gwt() {
  case "$1" in
    add)
      local branch="$2"
      [[ -z "$branch" ]] && echo "Usage: gwt add <branch-name>" && return 1
      git worktree add "../$(basename $(pwd))-${branch}" "$branch"
      ;;
    list)
      git worktree list
      ;;
    remove)
      git worktree remove "$2"
      ;;
    *)
      echo "Usage: gwt {add|list|remove} [branch-name]"
      ;;
  esac
}

# ==================================================
# BAT THEME
# ==================================================
export BAT_THEME="Catppuccin Macchiato"

# ==================================================
# DELTA (GIT DIFF) CONFIGURATION
# ==================================================
export GIT_PAGER="delta"

# ==================================================
# MANPAGER (colorful man pages with bat)
# ==================================================
export MANPAGER="sh -c 'col -bx | bat -l man -p'"
export MANROFFOPT="-c"

# ==================================================
# UI ENHANCEMENTS
# ==================================================

# Beam cursor
echo -ne '\e[5 q'

# Better less colors
export LESS_TERMCAP_mb=$'\e[1;32m'      # begin bold
export LESS_TERMCAP_md=$'\e[1;34m'      # begin blink
export LESS_TERMCAP_me=$'\e[0m'         # reset bold/blink
export LESS_TERMCAP_so=$'\e[01;47;34m'  # begin reverse video
export LESS_TERMCAP_se=$'\e[0m'         # reset reverse video
export LESS_TERMCAP_us=$'\e[1;35m'      # begin underline
export LESS_TERMCAP_ue=$'\e[0m'         # reset underline

# Enable true color support
export COLORTERM=truecolor

# Better colors for ls
export CLICOLOR=1

# ==================================================
# KUBERNETES ENVIRONMENT
# ==================================================

# Tool completions are loaded together, deferred until just after compinit (run
# by the turbo block's `zicompinit`), because each emits `compdef` calls that
# require compinit first. Invoked from fast-syntax-highlighting's atinit. Each
# is guarded by command -v and cached via _evalcache, so cost is negligible.
_wkst_load_tool_completions() {
  command -v kubectl   >/dev/null && _evalcache kubectl completion zsh
  command -v helm      >/dev/null && _evalcache helm completion zsh
  command -v gh        >/dev/null && _evalcache gh completion -s zsh
  command -v kind      >/dev/null && _evalcache kind completion zsh
  command -v k9s       >/dev/null && _evalcache k9s completion zsh
  command -v kustomize >/dev/null && _evalcache kustomize completion zsh
  command -v just      >/dev/null && _evalcache just --completions zsh
  command -v rustup    >/dev/null && _evalcache rustup completions zsh
  # kubecolor shares kubectl's completion (it's a passthrough wrapper).
  command -v kubecolor >/dev/null && compdef kubecolor=kubectl
}


# ==================================================
# Attach TMUX (interactive top-level shells only)
# ==================================================
# Guards: only attach when this is an interactive top-level shell, the
# terminal is a TTY, tmux is installed, and we're not already inside one.
# Without these guards, non-interactive shells (e.g. agents, IDE shells,
# scripts) would deadlock or fail with "open terminal failed".
if [[ $- == *i* ]] && [[ -t 1 ]] && [[ -z "$TMUX" ]] \
   && [[ -z "$VSCODE_INJECTION" ]] && [[ "$TERM_PROGRAM" != "vscode" ]] \
   && [[ -z "$INSIDE_EMACS" ]] && [[ "$WKST_NO_TMUX" != "1" ]] \
   && command -v tmux >/dev/null; then
  exec tmux new-session -A -s TMUX
fi

# ==================================================
# POST-INIT VISUALS
# ==================================================
# Welcome message — only on the first shell of a session, not every tmux pane.
# (Outside tmux: always; inside tmux: only window 1, pane 1.) Set
# WKST_NO_GREETER=1 to disable entirely.
_wkst_show_greeter() {
  [[ $- != *i* ]] && return 1
  [[ "$WKST_NO_GREETER" == "1" ]] && return 1
  [[ -z "$TMUX" ]] && return 0
  [[ "$(tmux display -p '#{window_index}.#{pane_index}' 2>/dev/null)" == "1.1" ]]
}

if _wkst_show_greeter; then
  clear
  # Visual init: a random shell-color-script (installed via wkst bootstrap).
  command -v colorscript >/dev/null && colorscript -r
  echo

  # Show current k8s context on shell start
  if command -v kubectl >/dev/null && command -v kubectx >/dev/null; then
    current_ctx=$(kubectx -c 2>/dev/null)
    if [[ -n "$current_ctx" ]]; then
      if [[ "$current_ctx" == *"prod"* ]]; then
        echo "\033[1;31m⎈ Kubernetes context: $current_ctx\033[0m"
      else
        echo "\033[1;32m⎈ Kubernetes context: $current_ctx\033[0m"
      fi
    fi
  fi

  # Show git status if in git repo
  if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "\033[1;34m$(git branch --show-current 2>/dev/null)\033[0m"
  fi

  # Rotating discovery tip — surface one lesser-known helper each session.
  # See docs/terminal-command-discovery.md for the full reference.
  local -a _wkst_tips=(
    "Press Ctrl-G for navi cheats, or ask in plain English: howto <what you want>"
    "Fuzzy-switch git branches: gbr   (or gco with no args)"
    "Jump to a frecent dir: z <name>   ·   pick interactively: zi"
    "Shell into a pod: ksh   ·   tail pod logs: klf   ·   switch context: kctx"
    "Kill a process interactively: fkill"
    "Find & edit with preview: fv   ·   find & cd: fcd   ·   make+enter dir: mkcd"
    "Quick examples for any tool: tldr <cmd>   ·   from the web: cheat <cmd>"
    "Full command tour: wkst help   ·   reference: docs/terminal-command-discovery.md"
  )
  echo "\033[2;37m💡 ${_wkst_tips[$((RANDOM % ${#_wkst_tips[@]} + 1))]}\033[0m"

  echo
fi

# ==================================================
# VI MODE CURSOR CONTROL
# ==================================================
# Change cursor shape based on vi mode (beam in insert, block in command).
function _cursor_update() {
  if [[ $KEYMAP == vicmd ]]; then
    printf '\e[2 q'   # block cursor in command mode
  else
    printf '\e[5 q'   # beam cursor in insert mode
  fi
}

function zle-keymap-select {
  _cursor_update
}

function zle-line-init {
  _cursor_update
}

# Return to beam cursor after command execution
function zle-line-finish {
  printf '\e[5 q'
}

zle -N zle-keymap-select
zle -N zle-line-init
zle -N zle-line-finish

# ==================================================
# CONTEXT-RICH TERMINAL / TAB TITLE
# ==================================================
# Window title (OSC 2): "<pwd> · <git branch> · ⎈ <k8s context>" so the context
# stays visible when the terminal is unfocused. Tab title (OSC 1): just the dir
# name. oh-my-posh's own title is disabled (console_title_template removed from
# base.json) so there is a single writer. Registered after oh-my-posh init so it
# wins the precmd ordering. Interactive shells only.
function _wkst_set_title() {
  [[ -o interactive ]] || return
  local dir="${PWD/#$HOME/~}"
  local parts="$dir"
  local branch
  branch="$(git symbolic-ref --short HEAD 2>/dev/null)"
  [[ -n "$branch" ]] && parts="${parts}  ${branch}"
  if command -v kubectl >/dev/null 2>&1; then
    local ctx
    ctx="$(kubectl config current-context 2>/dev/null)"
    [[ -n "$ctx" ]] && parts="${parts}  ⎈ ${ctx}"
  fi
  printf '\e]2;%s\a' "$parts"      # window title
  printf '\e]1;%s\a' "${dir:t}"    # tab/icon title
}
typeset -ag precmd_functions
precmd_functions+=(_wkst_set_title)

# ==================================================
# ATUIN CONFIGURATION
# ==================================================
# Additional atuin settings if installed
if command -v atuin >/dev/null; then
  export ATUIN_NOBIND="true"
  bindkey '^r' _atuin_search_widget

  # ALT+↑ for atuin search
  bindkey '^[[1;3A' _atuin_search_widget
fi

# ==================================================
# COMMAND DISCOVERY  (navi + `howto` + smart fallbacks)
# ==================================================
# Three intuitive ways to answer "what do I run to do X?":
#   1. Ctrl-G        — navi: fuzzy-search curated cheats by intent, fills args.
#   2. howto "..."   — natural language -> command via the local Claude CLI.
#   3. bare commands — a few short commands open an fzf picker when given no args.
# Full reference: docs/terminal-command-discovery.md in the config-workstation repo.

# navi widget: Ctrl-G opens the cheat picker and drops the chosen command on the
# line for editing (never auto-runs). Cached for fast startup.
if command -v navi >/dev/null; then
  _evalcache navi widget zsh
fi

# howto: plain-English request -> a single shell command, placed on the command
# line for review (NOT executed). Prefers the modern tools installed here.
howto() {
  if [[ -z "$*" ]]; then
    print -u2 "usage: howto <what you want to do>"
    print -u2 "   e.g. howto find files over 100MB changed today"
    return 1
  fi
  if ! command -v claude >/dev/null; then
    print -u2 "howto: claude CLI not installed"
    return 1
  fi
  local prompt="You are a shell expert on a macOS/Linux SRE workstation. These modern CLI tools are installed and PREFERRED over legacy equivalents: rg fd eza bat fzf zoxide jq yq dasel jless duckdb delta difftastic lazygit gh kubectl k9s k8sgpt stern kubeshark helm xh hurl grpcurl oha k6 btop procs dust duf bandwhich gping trippy hyperfine pgcli mycli harlequin trivy grype syft cosign trufflehog sops yazi. Translate the request into a SINGLE shell command line. Output ONLY the command — no explanation, no markdown fences, no backticks. Request: $*"
  local cmd
  cmd="$(claude -p "$prompt" 2>/dev/null)" || { print -u2 "howto: query failed"; return 1; }
  cmd="${cmd//\`/}"                      # strip stray backticks
  cmd="${cmd%%$'\n'*}"                   # keep only the first line
  if [[ -n "${cmd// /}" ]]; then
    print -z "$cmd"                      # push to the edit buffer for review
  else
    print -u2 "howto: no suggestion"
    return 1
  fi
}

# Smart interactive fallbacks: a short command with NO args opens a fuzzy picker;
# with args it passes straight through. Guarded to interactive shells so scripts
# are never affected.
#
# Drop the `gco` alias on its own line FIRST — otherwise zsh expands it while
# parsing the function-defining block below and errors ("defining function based
# on alias"). This statement executes before that block is parsed.
unalias gco 2>/dev/null
if [[ $- == *i* ]]; then
  gco() {
    if (( $# )); then
      git checkout "$@"
    else
      local b
      b="$(git branch --all | grep -v HEAD | sed 's/[ *]//g; s#remotes/origin/##' | sort -u \
            | fzf --preview 'git log --oneline --color=always {} 2>/dev/null | head -50')" || return
      [[ -n "$b" ]] && git switch "$b"
    fi
  }
fi
