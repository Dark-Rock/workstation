-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

local opt = vim.opt

-- ==============================
-- INDENTATION (Your preference: 4 spaces)
-- ==============================
opt.tabstop = 4
opt.softtabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smarttab = true
opt.breakindent = true

-- ==============================
-- VISUAL FEEDBACK
-- ==============================
opt.showmatch = true -- Highlight matching brackets
opt.ruler = true -- Show cursor position
opt.scrolloff = 8 -- Keep 8 lines above/below cursor (LazyVim default is 4)

-- ==============================
-- FILE HANDLING
-- ==============================
opt.autowrite = true -- Auto-save before certain commands
opt.confirm = true -- Prompt before closing unsaved files

-- ==============================
-- FORMATTING
-- ==============================
opt.formatoptions:append("cro") -- Auto-wrap comments
vim.g.autoformat = false -- Disable LazyVim's format-on-save

-- ==============================
-- NAVIGATION
-- ==============================
opt.relativenumber = true -- Relative line numbers for faster motions

-- ==============================
-- UNDO
-- ==============================
opt.undofile = true -- Persist undo history across sessions
