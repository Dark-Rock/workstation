-- Additive, low-risk plugins + a Python formatter override. None of these change
-- existing keymaps; new maps live under <leader> to avoid collisions.
return {
  -- oil.nvim: edit the filesystem like a normal buffer (rename/move/delete as
  -- text). Complements neo-tree, which stays the sidebar tree.
  {
    "stevearc/oil.nvim",
    cmd = "Oil",
    keys = {
      { "<leader>o", "<cmd>Oil<cr>", desc = "Oil (edit parent dir)" },
    },
    opts = {
      view_options = { show_hidden = true },
    },
    dependencies = { "nvim-tree/nvim-web-devicons" },
  },

  -- diffview.nvim: side-by-side diffs + file/branch history (review large changes).
  {
    "sindrets/diffview.nvim",
    cmd = { "DiffviewOpen", "DiffviewFileHistory" },
    keys = {
      { "<leader>gdd", "<cmd>DiffviewOpen<cr>", desc = "Diffview: open" },
      { "<leader>gdf", "<cmd>DiffviewFileHistory %<cr>", desc = "Diffview: file history" },
      { "<leader>gdc", "<cmd>DiffviewClose<cr>", desc = "Diffview: close" },
    },
  },

  -- Python: format with ruff (black dropped). ruff also sorts imports.
  {
    "stevearc/conform.nvim",
    optional = true,
    opts = {
      formatters_by_ft = {
        python = { "ruff_organize_imports", "ruff_format" },
      },
    },
  },
}
