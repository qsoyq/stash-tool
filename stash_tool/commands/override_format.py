from pathlib import Path

import typer
import yaml
from typer_utils.utils import error

from stash_tool.commands import default_invoke_without_command

help_text = """
格式化 Stash 覆写文件
"""
cmd = typer.Typer(help=help_text)


def add_default_invoke():
    for _cmd in (cmd,):
        _cmd.callback(invoke_without_command=True)(default_invoke_without_command)


add_default_invoke()


class StashYamlDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super(StashYamlDumper, self).increase_indent(flow, indentless=False)


def represent_dict_with_quoted_keys(dumper, data):
    mapping = []
    for key, value in data.items():
        if isinstance(key, str):
            key_node = dumper.represent_scalar('tag:yaml.org,2002:str', key, style=None)
        else:
            key_node = dumper.represent_data(key)

        match key:
            case 'desc':
                value_node = dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|')
            case _:
                value_node = dumper.represent_data(value)
        mapping.append((key_node, value_node))
    return yaml.MappingNode('tag:yaml.org,2002:map', mapping)


def iterdir(path: Path, inplace: bool, verbose: bool, indent: int = 4):
    for p in path.iterdir():
        if p.is_dir():
            iterdir(p, inplace, verbose)

        if p.suffix == '.stoverride':
            YamlStoverrideFormatter(p, inplace, verbose, indent).update()


class YamlStoverrideFormatter:
    def __init__(self, path: Path, inplace: bool, verbose: bool, indent: int):
        assert path.exists() and path.is_file()
        data = yaml.safe_load(path.read_text())
        self.path = path
        self.data = data
        self.inplace = inplace
        self.verbose = verbose
        self.indent = indent

    def update(self, write: bool = True):
        self.add_force_http_engine()
        if write:
            self.write()

    def add_force_http_engine(self):
        data = self.data
        verbose = self.verbose
        p = self.path
        inplace = self.inplace

        # 仅对存在重写、改写的情况下需要添加`force-http-engine`
        _http = data.get('http', {}) or {}
        if len({k: v for k, v in _http.items() if k.lower() not in ('mitm', 'force-http-engine')}) == 0:
            return
        force = set((data.get('http') or {}).get('force-http-engine') or [])
        mitm: set[str] = set((data.get('http') or {}).get('mitm') or [])
        for item in mitm:
            # - 表示 mitm 白名单，跳过
            if item.startswith('-'):
                continue

            if item not in force:
                force.add(item)
                if verbose:
                    typer.echo(f"{p} -> {item}")

        if force and inplace:
            http_payload = {}
            http_payload['mitm'] = sorted(data['http']['mitm'])
            http_payload['force-http-engine'] = sorted(list(force))
            http_payload.update(data['http'])
            data['http'] = http_payload

    def write(self):
        self.path.write_text(self.dump())

    def dump(self) -> str:
        data = self.data
        indent = self.indent
        StashYamlDumper.add_representer(dict, represent_dict_with_quoted_keys)
        return yaml.dump(data, Dumper=StashYamlDumper, allow_unicode=True, indent=indent, width=9999, sort_keys=False)


@cmd.command()
def run(path: Path = typer.Argument('.', help='对指定路径的覆写文件或目录进行处理'), inplace: bool = typer.Option(False, help='是否直接修改对应的覆写文件'), verbose: bool = typer.Option(True)):
    """处理指定路径下的覆写文件, 添加force-http-engine"""
    if not path.exists():
        typer.echo(error('dirpath must be valid dir'))
        raise typer.Exit(1)

    if path.is_file() and path.suffix == '.stoverride':
        YamlStoverrideFormatter(path, inplace, verbose, 4).update()
    else:
        iterdir(path, inplace, verbose, 4)


if __name__ == '__main__':
    cmd()
