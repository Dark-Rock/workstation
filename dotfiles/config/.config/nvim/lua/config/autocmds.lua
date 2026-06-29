-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here

-- Disable line numbers on the dashboard (they appear briefly before the UI settles)
vim.api.nvim_create_autocmd({ "VimEnter", "WinEnter" }, {
  group = vim.api.nvim_create_augroup("NoNumbersDashboard", { clear = true }),
  callback = function()
    if vim.bo.filetype == "dashboard" then
      vim.opt_local.number = false
      vim.opt_local.relativenumber = false
      vim.opt_local.list = false
    end
  end,
})
