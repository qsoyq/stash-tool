import typer

import stash_tool.commands.http_catpure_parser
import stash_tool.commands.override_format
from stash_tool.commands import default_invoke_without_command

helptext = """
toolkit for iOS Stash VPN.
"""

cmd = typer.Typer(help=helptext)
cmd.add_typer(stash_tool.commands.override_format.cmd, name='stash-override-format')
cmd.add_typer(stash_tool.commands.http_catpure_parser.cmd, name='stash-http-capture-parser')


def add_default_invoke():
    for _cmd in (cmd,):
        _cmd.callback(invoke_without_command=True)(default_invoke_without_command)


add_default_invoke()

if __name__ == '__main__':
    cmd()
