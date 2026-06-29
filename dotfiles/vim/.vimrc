" ==============================
" BASIC SETTINGS
" ==============================
syntax on                           " Enable syntax highlighting
filetype plugin indent on           " Enable filetype detection, plugin, and indent
set encoding=utf-8                  " Use UTF-8 encoding
set fileencodings=utf-8             " File encoding fallback

" ==============================
" INDENTATION & TABS
" ==============================
set tabstop=4                       " Number of spaces tabs count for
set softtabstop=4                   " Number of spaces inserted when pressing Tab
set shiftwidth=4                    " Number of spaces for indentation
set expandtab                       " Use spaces instead of tabs
set autoindent                      " Copy indent from previous line
set smartindent                     " Smart auto-indent for C-like languages
set smarttab                        " Tabs behave intelligently
set breakindent                     " Wrapped lines maintain indentation

" ==============================
" LINE NUMBERS & CURSOR
" ==============================
set number                          " Show absolute line numbers
set relativenumber                  " Show relative line numbers
set cursorline                      " Highlight current line
set scrolloff=8                     " Keep 8 lines above/below cursor
set sidescrolloff=8                 " Horizontal scroll padding
set signcolumn=yes                  " Always show sign column
set laststatus=3                    " Global statusline
set showmatch                       " Highlight matching brackets
set ruler                           " Show cursor position in statusline

" ==============================
" VISUAL FEEDBACK
" ==============================
set nolist                              " Don't show invisible characters
" set list                              " Show invisible characters
" set listchars=tab:▸\ ,trail:·,extends:…,precedes:…  " Customize invisible chars

" ==============================
" SEARCHING
" ==============================
set incsearch                        " Incremental search
set hlsearch                         " Highlight search results
set ignorecase                       " Case-insensitive search
set smartcase                        " Case-sensitive if uppercase used

" ==============================
" MOUSE & CLIPBOARD
" ==============================
set mouse=a                          " Enable mouse in all modes
set clipboard+=unnamedplus           " Use system clipboard

" ==============================
" PERFORMANCE & FILE HANDLING
" ==============================
set hidden                           " Keep buffers open when switching
set noerrorbells                     " Disable error bells
set noswapfile                       " Disable swap files
set nobackup                         " Disable backup files

" ==============================
" Persistent Undo Setup
" ==============================
if has('persistent_undo')
    " Expand $HOME reliably
    let undo_dir = expand('$HOME/.vim/undodir')

    " Create directory if it doesn't exist
    if !isdirectory(undo_dir)
        call mkdir(undo_dir, 'p', 0700)
    endif

    " Set undo directory and enable persistent undo
    execute 'set undodir=' . undo_dir
    set undofile
endif

set updatetime=300                   " Faster CursorHold events
set lazyredraw                       " Do not redraw while executing macros
set ttyfast                          " Optimize redraw speed

" ==============================
" COMMAND LINE & AUTOCOMPLETE
" ==============================
set wildmenu                          " Enhanced command-line completion
set wildmode=list:longest,full        " Better tab completion behavior
set showcmd                           " Show partial commands while typing
set confirm                           " Prompt before closing unsaved files
set autowrite                         " Auto-save before certain commands

" ==============================
" FORMATTING
" ==============================
set formatoptions+=cro                " Auto-wrap comments nicely

" ==============================
" VISUAL
" ==============================
augroup NoNumbersDashboard
  autocmd!
  autocmd VimEnter,WinEnter *
        \ if &filetype ==# 'dashboard' |
        \   setlocal nonumber norelativenumber nolist |
        \ endif
augroup END

" ==============================
" KEYBINDS
" ==============================
inoremap jj <Esc>
nnoremap n o<Esc>
nnoremap <C-n> n

" Multiple cursor "
nnoremap <S-b> <C-v>
vnoremap <S-b> <C-v>

inoremap <C-u> <C-r>
nnoremap <C-u> <C-r>
vnoremap <C-u> <C-r>

nnoremap <C-c> y
vnoremap <C-c> y

" Ctrl X "
nnoremap <C-x> dd
vnoremap <C-x> d

" Ctrl Z undo "
inoremap <C-z> u
nnoremap <C-z> u
vnoremap <C-z> u

" Leader-based ergonomics that preserve native Vim behavior "
nnoremap <leader>y "+y
vnoremap <leader>y "+y
nnoremap <leader>Y "+Y
nnoremap <leader>p "+p
vnoremap <leader>p "+p
nnoremap <leader>d "_d
vnoremap <leader>d "_d
nnoremap <leader>c "_c
vnoremap <leader>c "_c
nnoremap <leader>tn o<Esc>
nnoremap <leader>tN O<Esc>
