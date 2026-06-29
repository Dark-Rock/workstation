# Terminal Configuration Quick Reference

## tmux Keybindings

### Prefix Key
- **Prefix**: `Ctrl-s` (not the default `Ctrl-b`)

### Essential Operations
- `Prefix + r` - Reload tmux config
- `Prefix + ?` - Show all keybindings

### Pane Management
- `Prefix + |` - Split pane vertically (new pane to the right)
- `Prefix + -` - Split pane horizontally (new pane below)
- `Prefix + h/j/k/l` - Navigate panes (vim-style)
- `Prefix + H/J/K/L` - Resize panes (hold and repeat)
- `Prefix + z` - Toggle pane zoom (fullscreen)
- `Prefix + Ctrl-s` - Toggle to last pane
- `Prefix + x` - Kill current pane (no confirmation)

### Window Management
- `Prefix + c` - Create new window
- `Prefix + Tab` - Toggle to last window
- `Prefix + X` - Kill current window (no confirmation)
- `Prefix + ,` - Rename window
- `Alt + Shift + H` - Previous window (no prefix needed)
- `Alt + Shift + L` - Next window (no prefix needed)

### Session Management
- `Prefix + Ctrl-c` - Create new session
- `Prefix + Ctrl-f` - Find and switch to session (fuzzy search)
- `Prefix + Shift-Tab` - Toggle to last session
- `Alt + p` - Previous session (no prefix needed)
- `Alt + n` - Next session (no prefix needed)
- `Prefix + d` - Detach from session

### Copy Mode (Vi-style)
- `Prefix + [` - Enter copy mode
- `v` - Start selection (in copy mode)
- `Ctrl-v` - Rectangle selection (in copy mode)
- `y` - Copy selection to clipboard (in copy mode)
- `q` - Exit copy mode

### Advanced Features
- `Prefix + F` - Tmux Thumbs - Show hints for URLs/paths/hashes to copy
- `Prefix + Ctrl-f` - FZF menu for sessions/windows/panes

### Status Bar Indicators
- **Left**: Session name
- **Right**:
  - Application status
  - **K8s context** (shows current kubectl context)
  - **Hostname** (useful for SSH sessions)
  - **Current directory** (basename only)
  - **Date/Time**

### Session Persistence
- Sessions auto-save every 15 minutes
- Sessions auto-restore on tmux start
- All pane contents are saved
- Nvim sessions are preserved

---

## Ghostty Keybindings

### Tab Management
- `Cmd + t` - New tab
- `Cmd + Shift + ]` - Next tab
- `Cmd + Shift + [` - Previous tab
- `Cmd + w` - Close current tab/split

### Split Management
- `Cmd + Shift + d` - Split right (vertical split)
- `Cmd + Shift + Shift + d` - Split down (horizontal split)

### Split Navigation (Vim-style)
- `Cmd + h` - Move to left split
- `Cmd + j` - Move to bottom split
- `Cmd + k` - Move to top split
- `Cmd + l` - Move to right split

### Font Size
- `Cmd + =` - Increase font size
- `Cmd + -` - Decrease font size
- `Cmd + 0` - Reset font size

### Search
- `Cmd + f` - Search in scrollback

### Config
- `Cmd + Shift + c` - Reload Ghostty config

---

## Workflow Tips

### Kubernetes Workflow
1. **Check current context**: Status bar shows K8s context automatically
2. **Switch context**: Use `kubectx` in terminal (installed)
3. **Visual K8s**: Use `k9s` for interactive cluster management
4. **Pod logs**: Use `stern` for multi-pod log tailing

### SSH Workflow
1. **Status bar shows hostname** when SSH'd to remote server
2. **Multiple SSH sessions**: Create new panes/windows for different servers
3. **Session per server**: Create named sessions (Prefix + Ctrl-c, then rename)

### Git Workflow
1. **LazyGit**: Type `lazygit` for interactive git UI
2. **Status in Oh-My-Posh**: Shell prompt shows git branch/status
3. **Delta diff**: Git diffs use `git-delta` with syntax highlighting

### Multi-Project Workflow
1. **Session per project**: Create session for each project
   ```bash
   tmux new-session -s project-name -c /path/to/project
   ```
2. **Quick switching**: Use `Prefix + Ctrl-f` to fuzzy-search sessions
3. **Auto-restore**: All sessions restore on restart
4. **Directory indicator**: Status bar shows current directory

### Copy/Paste Workflow
1. **Quick URL/path copy**: Use `Prefix + F` (Thumbs) to show hints
2. **Manual selection**: Enter copy mode, select with `v`, copy with `y`
3. **Mouse selection**: Select text with mouse, then `y` in copy mode

---

## First-Time Setup

### Install tmux Plugins
1. Open tmux
2. Press `Prefix + I` (capital i) to install all plugins
3. Wait for installation to complete
4. Press `Prefix + r` to reload config

### Verify Installation
- Check if K8s context appears in status bar (requires kubectl)
- Test split navigation with `Prefix + h/j/k/l`
- Test Thumbs with `Prefix + F`

### Optional: Custom Status Bar
To add more indicators (AWS profile, Git branch in tmux, etc.), edit:
- `~/.config/tmux/tmux.conf`
- Look for "Custom status modules" section
- Add more `#(command)` expressions

---

## Troubleshooting

### tmux Issues
- **Plugins not working**: Run `Prefix + I` to install
- **Status bar not showing K8s**: Ensure `kubectl` is in PATH
- **Colors look wrong**: Ensure `$TERM` is set to `tmux-256color`
- **Clipboard not working**: Check pbcopy (macOS) or xclip (Linux) is installed

### Ghostty Issues
- **Ligatures not working**: Ensure Nerd Font is installed
- **Vi mode cursor not changing**: Cursor change is handled by shell (.zshrc), not Ghostty
- **Keybindings not working**: Reload config with `Cmd + Shift + c`

### Performance Issues
- **Slow tmux**: Reduce status interval in config (currently 5 seconds)
- **Ghostty lag**: Reduce transparency or disable blur in config

---

## Configuration Files
- tmux: `~/.config/tmux/tmux.conf`
- Ghostty: `~/.config/ghostty/config`
- Zsh (vi mode): `~/.zshrc`
- This guide: `~/.config/TERMINAL_GUIDE.md`
