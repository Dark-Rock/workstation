-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Wrapper that always sets a `desc`, so every custom map shows up in which-key,
-- `<leader>?` (buffer keymaps), and `<leader>sk` (search keymaps).
local function map(mode, lhs, rhs, desc)
  vim.keymap.set(mode, lhs, rhs, { noremap = true, silent = true, desc = desc })
end

-- ==============================
-- MULTI-CURSOR (vim-visual-multi)
-- ==============================
map("n", "<C-j>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Down)", true, false, true), "n", true)
end, "Add cursor down")

map("n", "<C-k>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Up)", true, false, true), "n", true)
end, "Add cursor up")

map("v", "<C-j>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Down)", true, false, true), "n", true)
end, "Add cursor down")

map("v", "<C-k>", function()
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Plug>(VM-Add-Cursor-Up)", true, false, true), "n", true)
end, "Add cursor up")

-- ==============================
-- EDITING
-- ==============================
map("i", "jj", "<Esc>", "Escape insert mode")
map("n", "n", "o<Esc>", "Insert blank line below")
map("n", "<C-n>", "n", "Find next match")

-- Visual block mode (<C-v> is remapped to paste; <C-q> is the standard terminal alternative)
map("n", "<C-q>", "<C-v>", "Visual block mode")
map("n", "<S-b>", "<C-v>", "Visual block mode")
map("v", "<S-b>", "<C-v>", "Visual block mode")

-- Redo
map({ "i", "n", "v" }, "<C-u>", "<C-r>", "Redo")

-- Delete/change without overwriting Vim's unnamed register. Use <C-x> when you
-- actually want to cut to the system clipboard.
map({ "n", "v" }, "d", '"_d', "Delete without yanking")
map({ "n", "v" }, "c", '"_c', "Change without yanking")
map("n", "x", '"_x', "Delete character without yanking")
map("n", "X", '"_X', "Delete previous character without yanking")

local function cut_line_to_clipboard()
  vim.fn.setreg("+", vim.api.nvim_get_current_line(), "V")
  vim.cmd('normal! "_dd')
end

local function cut_selection_to_clipboard()
  local unnamed = vim.fn.getreg('"')
  local unnamed_type = vim.fn.getregtype('"')
  vim.cmd('normal! "+y')
  vim.fn.setreg('"', unnamed, unnamed_type)
  vim.cmd('normal! gv"_d')
end

-- Clipboard shortcuts
map("n", "<C-x>", cut_line_to_clipboard, "Cut line to system clipboard")
map("v", "<C-x>", cut_selection_to_clipboard, "Cut selection to system clipboard")

-- Leader-based ergonomics that preserve native Vim behavior
map({ "n", "v" }, "<leader>y", '"+y', "Yank to system clipboard")
map("n", "<leader>Y", '"+Y', "Yank line to system clipboard")
map({ "n", "v" }, "<leader>p", '"+p', "Paste from system clipboard")
map({ "n", "v" }, "<leader>d", '"_d', "Delete (black hole register)")
map({ "n", "v" }, "<leader>c", '"_c', "Change (black hole register)")
map("n", "<leader>tn", "o<Esc>", "Blank line below")
map("n", "<leader>tN", "O<Esc>", "Blank line above")
