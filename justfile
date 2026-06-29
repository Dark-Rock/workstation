# wkst — workstation management tasks.
# Run `just` with no args to list everything.

set shell := ["bash", "-cu"]

# Default: list available recipes.
default:
    @just --list

# Install the `wkst` CLI globally so you can call it from anywhere.
# Editable install: `git pull` updates apply immediately with no reinstall.
install-cli:
    uv tool install --editable . --force
    @echo
    @echo "Installed: $(which wkst)"
    @echo "Try: wkst help"

# Uninstall the global `wkst` binary.
uninstall-cli:
    uv tool uninstall wkst

# Validate the package manifest.
validate:
    uv run wkst manifest validate

# Verify generated docs match packages.toml.
docs-check:
    @tmp="$$(mktemp)"; \
    uv run wkst manifest render-md > "$$tmp"; \
    diff -u TOOLS.md "$$tmp"; \
    rm -f "$$tmp"

# Show what would be installed without doing anything.
install-dry-run *args:
    uv run wkst install --dry-run {{args}}

# Install everything (packages + dotfiles + plugins).
install *args:
    uv run wkst install {{args}}

# Update everything (brew/apt/cargo/npm/pipx + plugins).
update *args:
    uv run wkst update {{args}}

# Health check: missing tools, dotfile drift, shell sanity.
doctor:
    uv run wkst doctor

# Symlink dotfiles into $HOME (stow-style).
sync *args:
    uv run wkst sync {{args}}

# Show diff between repo dotfiles and $HOME.
diff:
    uv run wkst diff

# Prune accumulated .bak.* files in $HOME.
clean *args:
    uv run wkst clean {{args}}

# Regenerate TOOLS.md from packages.toml.
docs:
    uv run wkst manifest render-md > TOOLS.md
    @echo "TOOLS.md regenerated"

# Run python tests.
test:
    uv run pytest tests/ -v

# Run python tests with compact CI output.
test-quiet:
    uv run pytest tests/ -q

# Lint Python sources.
lint:
    uv run ruff check wkst/ tests/

# Check Python formatting without modifying files.
fmt-check:
    uv run ruff format --check wkst/ tests/

# Format Python sources.
fmt:
    uv run ruff format wkst/ tests/

# Type-check Python sources.
typecheck:
    uv run mypy wkst tests
    uv run pyright wkst tests

# Lint shell sources.
lint-sh:
    if command -v shellcheck >/dev/null 2>&1; then shellcheck bootstrap.sh; else echo "Skipping shellcheck (not installed)"; fi

# Lint GitHub Actions workflows.
lint-actions:
    if command -v actionlint >/dev/null 2>&1; then actionlint; else echo "Skipping actionlint (not installed)"; fi

# Format shell sources.
fmt-sh:
    if command -v shfmt >/dev/null 2>&1; then shfmt -w bootstrap.sh; else echo "Skipping shfmt (not installed)"; fi

# Check shell formatting.
fmt-sh-check:
    if command -v shfmt >/dev/null 2>&1; then shfmt -d bootstrap.sh; else echo "Skipping shfmt (not installed)"; fi

# Lint TOML sources.
lint-toml:
    if command -v taplo >/dev/null 2>&1; then taplo check packages.toml pyproject.toml; else echo "Skipping taplo (not installed)"; fi

# Format TOML sources.
fmt-toml:
    if command -v taplo >/dev/null 2>&1; then taplo fmt packages.toml pyproject.toml; else echo "Skipping taplo (not installed)"; fi

# Lint YAML sources.
lint-yaml:
    if command -v yamllint >/dev/null 2>&1; then yamllint .github/workflows/; else echo "Skipping yamllint (not installed)"; fi

# Lint markdown sources.
lint-md:
    if command -v markdownlint-cli2 >/dev/null 2>&1; then markdownlint-cli2 README.md TOOLS.md CLAUDE.md docs/*.md; else echo "Skipping markdownlint-cli2 (not installed)"; fi

# Run the bootstrap.sh in a clean container (Debian) for verification.
bootstrap-test:
    docker run --rm -v "$PWD":/repo -w /repo debian:12 \
        bash -c "apt-get update -qq && apt-get install -y -qq curl ca-certificates sudo && \
                 WKST_REPO_DIR=/repo WKST_SKIP_FINAL_INSTALL=1 bash bootstrap.sh"

# Run all CI checks locally.
ci: lint fmt-check lint-sh fmt-sh-check lint-actions lint-yaml lint-md lint-toml test-quiet validate docs-check install-dry-run
    @echo "All CI checks passed"

# Run slower container bootstrap checks locally.
ci-full: ci bootstrap-test
    @echo "Full CI checks passed"
