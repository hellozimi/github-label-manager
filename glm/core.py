import argparse
import os
import sys
import struct

import requests

from colored import (
    fg,
    bg,
    attr
)
from x256 import x256

from . import cli
from . import utils
from .argument_helpers import (
    RepoArg,
    ColorArg,
    ShowColorArg,
    NameArg
)
from .config import (
    __github_url__,
    __token_file__
)


""" Initialize cli program """
cli.init(
    prog='glm',
    description='''Github label manager, helps managing your github issue
                    labels.''',
    epilog="Source: https://github.com/hellozimi/github-label-manager"
)


@cli.command(
    'auth',
    help='''Authenticate glm with your personal access token obtained at
            https://github.com/settings/tokens. This step is required for the
            program to work.'''
)
@cli.argument(
    'token',
    action='store',
    help='Github personal access token.',
    metavar='<access token>'
)
def auth_command(args):
    """ Parses the authentication command.
    Stores a file at __token_file__ with the personal access token in it.

    Args:
        args: Object with a personal github token string in it
    """

    f = open(__token_file__, 'w', encoding='utf-8')
    print(args.token, file=f)
    f.close()
    print('🚀  Authentication stored!')


@cli.command('list', help='List all labels in repository.')
@cli.argument('repo',
    **RepoArg(help='The repository you want to list labels from.')
)
@cli.argument('--show-colors', **ShowColorArg())
def list_command(args):
    """ Parses the list command.
    Fetches the target repositry passed in args and prints a colored list

    Args:
        args: Object with repo in it

    """

    params = {'access_token': utils.get_access_token()}

    url = '{}/repos/{}/labels'.format(__github_url__, args.repo)
    r = requests.get(url, params=params)
    res = r.json()

    if len(res) == 0:
        print("\u2757  No labels found")
        sys.exit(0)

    spacing = len(max([x['name'] for x in res], key=len))
    for row in res:
        name = row['name']
        c = row['color']
        fmt = '{}{} {} {} {}'.format(
            bg(x256.from_hex(c)),
            fg(utils.text_color(c)),
            name.center(spacing),
            attr(0),
            '[#{}]'.format(c) if args.show_colors else '',
        )
        print(fmt)


@cli.command(
    'create',
    help='Create label with name and color'
)
@cli.argument(
    'repo',
    **RepoArg(help='The repository you want to add labels to.')
)
@cli.argument(
    '--name',
    **NameArg(
        required=True,
        help='Name of the label you want to create.'
    )
)
@cli.argument(
    '--color',
    **ColorArg(
        required=True,
        help='Color of the label you want to create in hex without # or 0x.'
    )
)
def create_command(args):
    """ Parses the create command.
    Creates a new label at the wanted location.

    Args:
        args: Object with repo, name and color in it

    """

    params = {'access_token': utils.get_access_token()}
    name = ' '.join(args.name)
    payload = {
        'name': name,
        'color': args.color
    }

    url = '{}/repos/{}/labels'.format(__github_url__, args.repo)
    r = requests.post(url, json=payload, params=params)

    if r.status_code == 201:
        print("\u2705  Label successfully created")
    else:
        res = r.json()
        errors = []
        if 'Validation Failed' in res.get('message', ''):
            for error in res.get('errors', []):
                errors.append(utils.parse_validation_error(name, error))

        if len(errors) == 0:
            errors.append("\u274c  Failed to create label.")

        print('\n'.join(errors))


@cli.command(
    'delete',
    help='Delete label from repository.'
)
@cli.argument(
    'repo',
    **RepoArg(help='The repository you want to add labels to.')
)
@cli.argument(
    'name',
    **NameArg(help='The name of the label you want to delete.')
)
@cli.argument(
    '-f', '--force',
    default=False,
    action='store_true',
    help='Pass --force if you don\'t want to confirm your action'
)
def delete_command(args):
    """ Parses the delete command.
    Deletes a label at the wanted location. Ask for confirmation unless
        -f/--force is passed

    Args:
        args: Object with repo and name in it. Optionally force as boolean.

    """

    name = ' '.join(args.name)
    question = '\u26d4  Are you sure you want to delete \'{}\'?'.format(name)
    prompt = ' [y/N] '
    while not args.force:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice == '' or choice == 'n' or choice == 'no':
            return
        elif choice == 'y' or choice == 'yes':
            break

    params = {'access_token': utils.get_access_token()}
    url = '{}/repos/{}/labels/{}'.format(__github_url__, args.repo, name)
    r = requests.delete(url, params=params)
    if r.status_code == 204:
        print("\U0001f5d1  Label successfully removed")
    elif r.status_code == 404:
        msg = '\U0001f6ab  The label \'{}\' doesn\'t exist in {}.'.format(
            name,
            args.repo
        )
        print(msg)
    else:
        print("\u274c  Failed to create label.")


@cli.command(
    'update',
    help='Update label with new name and/or color.'
)
@cli.argument('repo', **RepoArg(help='The repository you want to update a label at.'))
@cli.argument(
    'label_name',
    **NameArg(help='The name of the label you want to delete.')
)
@cli.argument(
    '--name',
    **NameArg(help='New name of the label you want to update.')
)
@cli.argument(
    '--color',
    **ColorArg(help='New color of the label you want to update in hex without'
                    '# or 0x.')
)
def update_command(args):
    if not any([args.color, args.name]):
        print('\U0001f6ab  You must pass either a --name and/or --color')
        sys.exit(1)

    name = ' '.join(args.label_name)
    params = {'access_token': utils.get_access_token()}
    url = '{}/repos/{}/labels/{}'.format(__github_url__, args.repo, name)

    payload = { k: v for k, v in vars(args).items()
                if k in ['color', 'name'] and v }

    if 'name' in payload:
        payload['name'] = ' '.join(payload['name'])

    r = requests.patch(url, json=payload, params=params)

    if r.status_code == 200:
        print("\u2705  Label successfully updated")
    else:
        res = r.json()
        errors = []
        if 'Validation Failed' in res.get('message', ''):
            for error in res.get('errors', []):
                errors.append(utils.parse_validation_error(name, error))

        if len(errors) == 0:
            errors.append("\u274c  Failed to update label.")

        print('\n'.join(errors))


def run():
    cli.parse()
