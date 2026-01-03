from pathlib import Path

import typer
import yaml
from typer_utils.utils import error

help_text = """
为指定目录下所有覆写文件补充 force-http-engine
"""
cmd = typer.Typer(help=help_text)


@cmd.callback(invoke_without_command=True)
def default(): ...


class MyDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super(MyDumper, self).increase_indent(flow, indentless=False)


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


def my_yaml_dump(data: dict, indent: int = 4):
    MyDumper.add_representer(dict, represent_dict_with_quoted_keys)
    return yaml.dump(data, Dumper=MyDumper, allow_unicode=True, indent=indent, width=9999, sort_keys=False)


def iterdir(path: Path, inplace: bool, verbose: bool, indent: int = 4):
    for p in path.iterdir():
        if p.is_dir():
            iterdir(p, inplace, verbose)

        if p.suffix == '.stoverride':
            update_stoverride(p, inplace, verbose, indent)


def update_stoverride(p: Path, inplace: bool, verbose: bool, indent: int):
    data = yaml.safe_load(p.read_text())
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
        p.write_text(my_yaml_dump(data, indent))


@cmd.command()
def run(path: Path = typer.Argument('.', help='对指定路径的覆写文件或目录进行处理'), inplace: bool = typer.Option(False, help='是否直接修改对应的覆写文件'), verbose: bool = typer.Option(True)):
    """处理指定路径下的覆写文件, 添加force-http-engine"""
    if not path.exists():
        typer.echo(error('dirpath must be valid dir'))
        raise typer.Exit(1)

    if path.is_file() and path.suffix == '.stoverride':
        update_stoverride(path, inplace, verbose, 4)
    else:
        iterdir(path, inplace, verbose, 4)


if __name__ == '__main__':
    cmd()
