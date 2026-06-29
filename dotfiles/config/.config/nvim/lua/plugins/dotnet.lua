-- .NET: use Microsoft's Roslyn language server (via seblyng/roslyn.nvim) instead
-- of OmniSharp. Roslyn is the engine behind VS Code's C# experience and is far
-- faster/more accurate on large solutions (e.g. the 28-project Dev.sln).
--
-- LazyVim's lang.dotnet extra wires OmniSharp; we disable it here so only Roslyn
-- attaches to .cs buffers. The Roslyn LSP isn't in the default Mason registry, so
-- we add the community registry that ships it.
--
-- To roll back: delete this file and re-run `:Lazy sync` (OmniSharp returns).
return {
  {
    "mason-org/mason.nvim",
    -- Add the community registry that ships the Roslyn LSP. We do NOT put
    -- "roslyn" in ensure_installed: at config-load time the community index
    -- isn't fetched yet, so an eager install throws and de-registers Mason's
    -- commands. Install it once with `:MasonInstall roslyn` (the registry is
    -- fetched on first `:Mason`), or `:MasonInstall roslyn-unstable` for bleeding edge.
    opts = {
      registries = {
        "github:mason-org/mason-registry",
        "github:Crashdummyy/mason-registry",
      },
    },
  },
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- Disable OmniSharp (configured by lazyvim ...lang.dotnet) in favour of Roslyn.
        omnisharp = { enabled = false },
      },
    },
  },
  {
    "seblyng/roslyn.nvim",
    ft = { "cs" },
    opts = {},
  },
}
