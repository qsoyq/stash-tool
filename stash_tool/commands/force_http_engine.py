import typer
from pathlib import Path
import yaml
from typer_utils.utils import error


help_text = """
为指定目录下所有覆写文件补充 force-http-engine 
"""
cmd = typer.Typer(help=help_text)


@cmd.callback(invoke_without_command=True)
def default(): ...


def iterdir(path: Path, inplace: bool, verbose: bool, indent: int = 4):
    for p in path.iterdir():
        if p.is_dir():
            iterdir(p, inplace, verbose)

        if p.suffix == ".stoverride":
            data = yaml.safe_load(p.read_text())
            force = set((data.get("http") or {}).get("force-http-engine") or [])
            mitm: set[str] = set((data.get("http") or {}).get("mitm") or [])
            for item in mitm:
                # - 表示 mitm 白名单，跳过
                if item.startswith("-"):
                    continue

                if item not in force:
                    force.add(item)
                    if verbose:
                        typer.echo(f"{p} -> {item}")

            if force and inplace:
                data["http"]["force-http-engine"] = list(force)
                p.write_text(yaml.safe_dump(data, allow_unicode=True, indent=indent))


@cmd.command()
def run(path: Path = typer.Argument("."), inplace: bool = typer.Option(False, help="是否直接修改对应的覆写文件"), verbose: bool = typer.Option(True)):
    """遍历路径并修改对应的覆写文件"""
    if not path.exists() or not path.is_dir:
        typer.echo(error("dirpath must be valid dir"))
        raise typer.Exit(1)

    iterdir(path, inplace, verbose)


if __name__ == "__main__":
    cmd()
