-- Discoverability for the workstation's intentionally non-standard keymaps.
--
-- Most custom maps now carry a `desc` (see lua/config/keymaps.lua), so they
-- already surface in which-key, `<leader>?` (buffer keymaps) and `<leader>sk`
-- (search keymaps). This spec adds one extra: an at-a-glance cheatsheet for the
-- few keys a Vim user would NOT guess (n inserts a line, find-next is <C-n>, …).
--
-- Bound to <leader>sK so it sits right next to LazyVim's <leader>sk
-- ("Search Keymaps"): lowercase = search all, uppercase = the surprising ones.
local function open_cheatsheet()
	local lines = {
		" Workstation key cheatsheet ",
		"",
		" These maps differ from stock Vim on purpose:",
		"",
		"   n            Insert blank line below   (find-next moved to <C-n>)",
		"   <C-n>        Find next match           (stock `n`)",
		"   jj           Escape insert mode",
		"   <C-j>/<C-k>  Add multi-cursor down/up  (vim-visual-multi)",
		"   <C-q>        Visual block mode         (<C-v> is paste)",
		"   <S-b>        Visual block mode",
		"   <C-x>        Cut line / selection",
		"   <C-u>        Redo                      (stock <C-r>)",
		"",
		" Leader clipboard helpers (preserve native Vim behavior):",
		"",
		"   <leader>y/Y  Yank to system clipboard",
		"   <leader>p    Paste from system clipboard",
		"   <leader>d    Delete to black hole register",
		"   <leader>c    Change to black hole register",
		"   <leader>tn   Blank line below   ·   <leader>tN  Blank line above",
		"",
		" <leader>sk searches ALL keymaps   ·   <leader>? shows buffer keymaps",
		"",
		" Press q or <Esc> to close.",
	}

	local buf = vim.api.nvim_create_buf(false, true)
	vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
	vim.bo[buf].modifiable = false
	vim.bo[buf].bufhidden = "wipe"
	vim.bo[buf].filetype = "markdown"

	local width = 0
	for _, line in ipairs(lines) do
		width = math.max(width, #line)
	end
	width = width + 2
	local height = #lines

	local win = vim.api.nvim_open_win(buf, true, {
		relative = "editor",
		width = width,
		height = height,
		row = math.floor((vim.o.lines - height) / 2),
		col = math.floor((vim.o.columns - width) / 2),
		style = "minimal",
		border = "rounded",
		title = " keys ",
		title_pos = "center",
	})
	vim.wo[win].cursorline = false

	for _, key in ipairs({ "q", "<Esc>" }) do
		vim.keymap.set("n", key, "<cmd>close<cr>", { buffer = buf, nowait = true, silent = true })
	end
end

vim.api.nvim_create_user_command("WkstKeys", open_cheatsheet, { desc = "Workstation key cheatsheet" })

return {
	{
		"folke/which-key.nvim",
		keys = {
			{ "<leader>sK", open_cheatsheet, desc = "Workstation key cheatsheet" },
		},
	},
}
