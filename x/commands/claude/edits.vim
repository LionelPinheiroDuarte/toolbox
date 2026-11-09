" Sourced by claude-edits when it opens a file in Vim.
" g:claude_before is the file as it was before Claude's edits ("" if no
" snapshot, "/dev/null" if Claude created the file).
"
"   ,d   git-diff-like view of Claude's changes, in a full-screen tab (q closes it)
"   ,D   side-by-side vimdiff, to undo a hunk with `do` (toggle; q quits both)

function! s:HasBefore() abort
  if empty(get(g:, 'claude_before', ''))
    echo 'no snapshot: edited before diffs were recorded'
    return 0
  endif
  if g:claude_before ==# '/dev/null'
    echo 'new file: created by Claude, nothing to diff'
    return 0
  endif
  return 1
endfunction

" Unified diff of the buffer (unsaved edits included) against Claude's "before".
function! s:ClaudeDiff() abort
  if !s:HasBefore()
    return
  endif
  let l:name = expand('%:p')
  let l:cmd = 'diff -u --label ' . shellescape('before (claude)')
        \ . ' --label ' . shellescape(l:name)
        \ . ' ' . shellescape(g:claude_before) . ' -'
  " as a string with the final newline the file will get on save: a list input
  " has none, which would show the last line as changed
  let l:text = join(getline(1, '$'), "\n") . (&eol || &fixeol ? "\n" : '')
  let l:out = systemlist(l:cmd, l:text)
  if empty(l:out)
    echo 'no changes left (reverted since Claude''s edit)'
    return
  endif

  tabnew
  call setline(1, l:out)
  execute 'silent file' fnameescape('[claude diff] ' . fnamemodify(l:name, ':t'))
  setlocal buftype=nofile bufhidden=wipe noswapfile nomodifiable readonly filetype=diff
  nnoremap <buffer> <silent> q :tabclose<CR>
  nnoremap <buffer> <silent> ,d :tabclose<CR>
endfunction

" Side-by-side vimdiff: Claude's "before" read-only on the left.
function! s:ClaudeSideBySide() abort
  " second ,D: close the diff, back to the plain file
  if exists('t:claude_before_buf') && bufexists(t:claude_before_buf)
    execute 'bwipeout' t:claude_before_buf
    unlet t:claude_before_buf
    diffoff!
    silent! nunmap <buffer> q
    return
  endif
  if !s:HasBefore()
    return
  endif

  " soft colors: changed lines get a dark tint, only the changed text stands out
  highlight DiffAdd    ctermbg=22  ctermfg=NONE cterm=NONE
  highlight DiffDelete ctermbg=NONE ctermfg=238 cterm=NONE
  highlight DiffChange ctermbg=236 ctermfg=NONE cterm=NONE
  highlight DiffText   ctermbg=24  ctermfg=NONE cterm=NONE

  let l:ft = &filetype
  let l:name = expand('%:t')
  diffthis
  nnoremap <buffer> <silent> q :qa<CR>

  leftabove vertical new
  execute 'silent read' fnameescape(g:claude_before)
  silent 1delete _
  execute 'silent file' fnameescape('[before claude] ' . l:name)
  setlocal buftype=nofile bufhidden=wipe noswapfile nomodifiable readonly
  let &l:filetype = l:ft
  nnoremap <buffer> <silent> q :qa<CR>
  diffthis
  let t:claude_before_buf = bufnr('%')

  wincmd l
endfunction

command! ClaudeDiff call s:ClaudeDiff()
command! ClaudeSideBySide call s:ClaudeSideBySide()
nnoremap <silent> ,d :ClaudeDiff<CR>
nnoremap <silent> ,D :ClaudeSideBySide<CR>
