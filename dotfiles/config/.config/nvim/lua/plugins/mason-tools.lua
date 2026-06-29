-- The Mason tool list is the single source of truth in `mason-tools.txt`
-- (at the nvim config root), shared with `wkst/plugins.py` so the two never
-- drift. One package per line; blank lines and `#` comments are ignored.
local function read_mason_tools()
	local path = vim.fn.stdpath("config") .. "/mason-tools.txt"
	if vim.fn.filereadable(path) == 0 then
		return {}
	end
	local tools = {}
	for _, line in ipairs(vim.fn.readfile(path)) do
		local trimmed = vim.trim(line)
		if trimmed ~= "" and not vim.startswith(trimmed, "#") then
			table.insert(tools, trimmed)
		end
	end
	return tools
end

return {
	{
		"mason-org/mason.nvim",
		opts = function(_, opts)
			opts.ensure_installed = opts.ensure_installed or {}
			vim.list_extend(opts.ensure_installed, read_mason_tools())
		end,
	},
}
