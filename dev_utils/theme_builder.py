#!/usr/bin/env python3
"""Build multiple versions of the docs with different themes.

If no THEME-NAME is given, all theme branches are built.

"""
import argparse
from pathlib import Path

import git
from sphinx.cmd.build import build_main

parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    'themes', metavar='THEME-NAME', nargs='*',
    help='theme name (according to "*-theme" branch name)')
args = parser.parse_args()

main_dir = Path(__file__).resolve().parent
repo = git.Repo(main_dir, search_parent_directories=True)

for remote in repo.remotes:
    if any('spatialaudio/nbsphinx' in url for url in remote.urls):
        theme_remote = remote
        break
else:
    raise ValueError('theme_remote not found')

themes = []
if args.themes:
    for remote_branch in theme_remote.refs:
        theme_name = remote_branch.remote_head[:-len('-theme')]
        if theme_name in args.themes:
            themes.append((theme_name, remote_branch.name))
            args.themes.remove(theme_name)
    if args.themes:
        parser.exit('theme(s) not found: {}'.format(args.themes))
else:
    for remote_branch in theme_remote.refs:
        if remote_branch.remote_head.endswith('-theme'):
            themes.append(
                (remote_branch.remote_head[:-len('-theme')], remote_branch.name))

worktree_dir = main_dir / '_worktree'
if not worktree_dir.exists():
    repo.git.worktree('prune')
    repo.git.worktree('add', worktree_dir, '--detach')

worktree = git.Git(worktree_dir)

head_commit = repo.git.rev_parse('HEAD')

worktree.reset(head_commit, '--hard')

stash_commit = repo.git.stash('create')

if stash_commit:
    worktree.merge(stash_commit)

base_commit = worktree.rev_parse('HEAD')

for name, branch in themes:
    print('\n\n')
    print('#' * 80)
    print('#', 'BUILDING: {}'.format(name.upper()).center(76), '#')
    print('#' * 80)
    worktree.cherry_pick(branch)
    build_args = [str(worktree_dir / 'doc'), str(main_dir / name)]
    # TODO: create proper release/version/today strings
    build_args.extend(['-Drelease=dummy', '-Dversion=dummy', '-Dtoday=dummy'])
    build_args.extend(['-Dhtml_title=nbsphinx'])
    build_args.extend(['-d', str(main_dir / '_cache')])
    if build_main(build_args) != 0:
        raise Exception('An Error occurred building the docs.')
    worktree.reset(base_commit, '--hard')

# TODO: use context manager to make sure this is done in the end:
worktree.reset(head_commit, '--hard')
