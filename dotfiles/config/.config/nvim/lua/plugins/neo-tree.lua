return {
	"nvim-neo-tree/neo-tree.nvim",
	keys = {
		{ "<leader>e", "<cmd>Neotree toggle<cr>", desc = "Toggle file explorer" },
		{ "<C-b>", "<cmd>Neotree toggle<cr>", desc = "Toggle file explorer" },
	},
	opts = {
		filesystem = {
			filtered_items = {
				visible = true,
				hide_dotfiles = false,
				hide_gitignored = false,
				hide_hidden = false,
			},
			follow_current_file = {
				enabled = true, -- Focuses file you're editing
			},
			use_libuv_file_watcher = true, -- Auto-refresh on file changes
		},
		window = {
			width = 30,
			mappings = {
				["<space>"] = "none", -- Disable space (conflicts with leader)
				["a"] = {
					"add",
					config = {
						show_path = "relative", -- Shows relative path when creating
					},
				},
				["A"] = "add_directory",
				["d"] = "delete",
				["r"] = "rename",
				["y"] = "copy_to_clipboard",
				["x"] = "cut_to_clipboard",
				["p"] = "paste_from_clipboard",
				["c"] = "copy", -- Copy file
				["m"] = "move", -- Move file
				["/"] = "fuzzy_finder",
				["H"] = "toggle_hidden",
				["<C-s>"] = "open_split",
				["<C-v>"] = "open_vsplit",
			},
		},
		default_component_configs = {
			git_status = {
				symbols = {
					added = "✚",
					modified = "",
					deleted = "✖",
					renamed = "󰁕",
					untracked = "",
					ignored = "",
					unstaged = "󰄱",
					staged = "",
					conflict = "",
				},
			},
		},
	},
}
