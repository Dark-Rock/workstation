-- every spec file under the "plugins" directory will be loaded automatically by lazy.nvim
--
-- In your plugin files, you can:
-- * add extra plugins
-- * disable/enabled LazyVim plugins
-- * override the configuration of LazyVim plugins
return {
	{
		"mg979/vim-visual-multi",
		branch = "master",
		event = "VeryLazy",
	},
	-- NOTE: kdheepak/lazygit.nvim was removed — LazyVim core already binds
	-- <leader>gg to Snacks.lazygit (same UX, one fewer plugin, no <leader>gg
	-- conflict). lazygit still opens with <leader>gg.
	{
		"akinsho/toggleterm.nvim",
		version = "*",
		keys = {
			{ "<C-\\>", "<cmd>ToggleTerm<cr>", desc = "Toggle terminal" },
		},
		opts = {
			direction = "float",
			float_opts = { border = "curved" },
		},
	},
	{
		"folke/todo-comments.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		opts = {},
		keys = {
			{ "<leader>ft", "<cmd>TodoTrouble<cr>", desc = "Find TODOs" },
		},
	},
}
