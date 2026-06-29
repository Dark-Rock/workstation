-- Ensure Homebrew binaries are visible to Neovim (must be set before lazy loads plugins)
vim.env.PATH = table.concat({
	"/opt/homebrew/bin",
	vim.env.PATH,
}, ":")

-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

-- Not writing any php code
vim.g.loaded_php_provider = 0
vim.g.loaded_julia_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0
