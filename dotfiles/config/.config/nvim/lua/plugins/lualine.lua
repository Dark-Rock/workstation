-- Lualine polish: surface high-signal editor state that LazyVim's defaults omit
-- (macro recording, search match count, visual selection size). The colorscheme
-- and the rest of LazyVim's lualine layout are intentionally left untouched —
-- no `theme` is set, so lualine inherits the active colorscheme. Colors below
-- reference theme highlight groups, so they adapt to whatever theme is active.
return {
  "nvim-lualine/lualine.nvim",
  opts = function(_, opts)
    opts.sections = opts.sections or {}
    local lualine_x = opts.sections.lualine_x or {}

    -- Macro recording indicator (e.g. "  REC @q"); blank when not recording.
    table.insert(lualine_x, 1, {
      function()
        local reg = vim.fn.reg_recording()
        if reg == "" then
          return ""
        end
        return "  REC @" .. reg
      end,
      color = "DiagnosticError",
    })
    -- Search match position (e.g. "[3/12]") and visual selection size.
    table.insert(lualine_x, 2, { "searchcount" })
    table.insert(lualine_x, 3, { "selectioncount" })

    opts.sections.lualine_x = lualine_x
    return opts
  end,
}
