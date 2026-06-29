-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local opts = { noremap = true, silent = true }

-- ==============================
-- MULTI-CURSOR (vim-visual-multi)
-- ==============================
vim.keymap.set("n", "<C-j>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Down)", true, false, true), "n", true)
end, opts)

vim.keymap.set("n", "<C-k>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Up)", true, false, true), "n", true)
end, opts)

vim.keymap.set("v", "<C-j>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Down)", true, false, true), "n", true)
end, opts)

vim.keymap.set("v", "<C-k>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Up)", true, false, true), "n", true)
end, opts)

-- ==============================
-- EDITING
-- ==============================
vim.keymap.set("i", "jj", "<Esc>", opts)
vim.keymap.set("n", "n", "o<Esc>", opts)
vim.keymap.set("n", "<C-n>", "n", opts)

-- Visual block mode (<C-v> is remapped to paste; <C-q> is the standard terminal alternative)
vim.keymap.set("n", "<C-q>", "<C-v>", opts)
vim.keymap.set("n", "<S-b>", "<C-v>", opts)
vim.keymap.set("v", "<S-b>", "<C-v>", opts)

-- Redo
vim.keymap.set({ "i", "n", "v" }, "<C-u>", "<C-r>", opts)

-- Clipboard shortcuts
vim.keymap.set("n", "<C-x>", "dd", opts)
vim.keymap.set("v", "<C-x>", "d", opts)
vim.keymap.set({ "i", "n", "v" }, "<C-z>", "u", opts)

-- Leader-based ergonomics that preserve native Vim behavior
vim.keymap.set({ "n", "v" }, "<leader>y", '"+y', opts)
vim.keymap.set("n", "<leader>Y", '"+Y', opts)
vim.keymap.set({ "n", "v" }, "<leader>p", '"+p', opts)
vim.keymap.set({ "n", "v" }, "<leader>d", '"_d', opts)
vim.keymap.set({ "n", "v" }, "<leader>c", '"_c', opts)
vim.keymap.set("n", "<leader>tn", "o<Esc>", opts)
vim.keymap.set("n", "<leader>tN", "O<Esc>", opts)
