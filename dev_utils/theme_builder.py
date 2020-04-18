import argparse
from pathlib import Path

import git
from sphinx.cmd.build import build_main

MAIN_DIR = Path(__file__).resolve().parent
CACHE_DIR = MAIN_DIR / '_cache'
WORKTREE_DIR = MAIN_DIR / '_worktree'
SOURCE_DIR = WORKTREE_DIR / 'doc'

repo = git.Repo(MAIN_DIR, search_parent_directories=True)

for remote in repo.remotes:
    if any('spatialaudio/nbsphinx' in url for url in remote.urls):
        theme_remote = remote
        break
else:
    raise ValueError('theme_remote not found')

themes = []
for remote_branch in theme_remote.refs:
    if remote_branch.remote_head.endswith('-theme'):
        themes.append(
            (remote_branch.remote_head[:-len('-theme')], remote_branch.name))

if not WORKTREE_DIR.exists():
    repo.git.worktree('prune')
    repo.git.worktree('add', WORKTREE_DIR, '--detach')

worktree = git.Git(WORKTREE_DIR)

head_commit = repo.git.rev_parse('HEAD')

worktree.reset(head_commit, '--hard')

stash_commit = repo.git.stash('create')

if stash_commit:
    worktree.merge(stash_commit)

base_commit = worktree.rev_parse('HEAD')

for name, branch in themes:
    print('\n\n')
    print('#' * 80)
    print('#', 'BUILDING BRANCH: {}'.format(name.upper()).center(76), '#')
    print('#' * 80)
    worktree.cherry_pick(branch)
    build_args = [str(SOURCE_DIR), str(MAIN_DIR / name)]
    # TODO: create proper release/version/today strings
    build_args.extend(['-Drelease=dummy', '-Dversion=dummy', '-Dtoday=dummy'])
    build_args.extend(['-Dhtml_title=nbsphinx'])
    build_args.extend(['-d', str(CACHE_DIR)])
    if build_main(build_args) != 0:
        raise Exception('An Error occurred building the docs.')
    worktree.reset(base_commit, '--hard')

# TODO: use context manager to make sure this is done in the end:
worktree.reset(head_commit, '--hard')
