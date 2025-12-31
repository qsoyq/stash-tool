import typer

from stash_tool.commands import default_invoke_without_command
import stash_tool.commands.force_http_engine

helptext = """
toolkit for iOS Stash VPN.
"""

cmd = typer.Typer(help=helptext)
cmd.add_typer(stash_tool.commands.force_http_engine.cmd, name="force-http-engine")


def add_default_invoke():
    for _cmd in (cmd,):
        _cmd.callback(invoke_without_command=True)(default_invoke_without_command)


add_default_invoke()

if __name__ == "__main__":
    cmd()
