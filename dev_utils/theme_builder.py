#!/usr/bin/env python3
"""Build multiple versions of the docs with different themes.

If no THEME-NAME is given, all theme branches are built.

"""
import argparse
from pathlib import Path

import git
from sphinx.cmd.build import build_main


def theme_branches(remote):
    for branch in remote.refs:
        if branch.remote_head.endswith('-theme'):
            yield branch.remote_head[:-len('-theme')], branch.name


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-themes', action='store_true',
    help='show list of available themes and exit')
args, remaining = parser.parse_known_args()

main_dir = Path(__file__).resolve().parent
repo = git.Repo(main_dir, search_parent_directories=True)
for remote in repo.remotes:
    if any('spatialaudio/nbsphinx' in url for url in remote.urls):
        theme_remote = remote
        break
else:
    raise ValueError('theme_remote not found')

if args.list_themes:
    for theme, _ in theme_branches(theme_remote):
        print(theme)
    parser.exit(0)

parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    'themes', metavar='THEME-NAME', nargs='*',
    help='theme name (according to "*-theme" branch name)')
args = parser.parse_args(remaining)

themes = theme_branches(theme_remote)
if args.themes:
    themes, potential_themes = [], themes
    for theme, branch in potential_themes:
        if theme in args.themes:
            themes.append((theme, branch))
            args.themes.remove(theme)
    if args.themes:
        parser.exit('theme(s) not found: {}'.format(args.themes))

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


def run_with_all_themes(func):
    try:
        for name, branch in themes:
            worktree.cherry_pick(branch)
            func(name, branch)
            worktree.reset(base_commit, '--hard')
    finally:
        worktree.reset(head_commit, '--hard')


def build_docs(name, branch):
    print('\n\n')
    print('#' * 80)
    print('#', 'BUILDING: {}'.format(name.upper()).center(76), '#')
    print('#' * 80)
    build_args = [str(worktree_dir / 'doc'), str(main_dir / name)]
    # TODO: create proper release/version/today strings
    build_args.extend(['-Drelease=dummy', '-Dversion=dummy', '-Dtoday=dummy'])
    build_args.extend(['-Dhtml_title=nbsphinx'])
    build_args.extend(['-d', str(main_dir / '_cache')])
    if build_main(build_args) != 0:
        raise Exception('An Error occurred building the docs.')


run_with_all_themes(build_docs)
