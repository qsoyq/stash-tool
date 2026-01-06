import json
import re
import sys
import traceback
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Generator

import httpx
import typer

from stash_tool.commands import default_invoke_without_command
from stash_tool.types.http_capture_parser import Body

help_text = """
Stash 抓包覆写日志分析工具

https://raw.githubusercontent.com/qsoyq/stash/main/override/debug/http-capture.stoverride
"""
cmd = typer.Typer(help=help_text)


def add_default_invoke():
    for _cmd in (cmd,):
        _cmd.callback(invoke_without_command=True)(default_invoke_without_command)


add_default_invoke()


def get_current_datetime_str() -> str:
    return datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')


def stdin_input() -> str:
    return sys.stdin.read()


def parse_json(text) -> tuple[dict | None, str | None]:
    try:
        body = json.loads(text)
        return (body, None)
    except json.decoder.JSONDecodeError as e:
        return (None, str(e))


def parse_log(file: Path) -> Generator[dict | None, None, None]:
    if not file.exists():
        typer.echo(f"path {file} not exists.")
        raise typer.Exit(1)

    if not file.is_file():
        typer.echo(f"path {file} must be file.")
        raise typer.Exit(2)

    for line in file.read_text().split('\n'):
        if line[12:16] == 'JSON':
            jsonstr = line[18:]
            body, err = parse_json(jsonstr)
            if err is not None:
                typer.echo(f"parse json error: {err}\traw:{jsonstr}")
            else:
                yield body


def fetch_media(url: str, prefix: str) -> None:
    try:
        typer.echo(f"url: {url}")
        parse_result = urllib.parse.urlparse(url)
        download_path = prefix + parse_result.netloc + parse_result.path[0] + parse_result.path[1:].replace('/', '-')
        resp = httpx.get(
            url,
            verify=False,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'},
        )
        if resp.is_error:
            typer.echo(f"fetch {url} error: {resp.status_code}, body: {resp.text}")
            return
        ct = resp.headers.get('content-type', '')
        ext = ''
        path = Path(download_path)
        try:
            if path.exists():
                typer.echo(f"file {path} exists, skip")
                return
        except OSError as e:
            if 'File name too long' in str(e):
                uid = uuid.uuid4().hex
                new_download_path = prefix + uid + ext
                new_path = Path(new_download_path)
                typer.echo(f"file name mapping: {path}->{new_path}")
                path = new_path
                if path.exists():
                    typer.echo(f"file {path} exists, skip")
                    return
            else:
                traceback.print_exc()
        path.parent.mkdir(parents=True, exist_ok=True)
        if ct.startswith('image/') or ct.startswith('video/'):
            ext = str(resp.headers.get('content-type', '')).split('/', 1)[-1]
            path = path.with_suffix(f".{ext}")
        if path.exists():
            typer.echo(f"file {path} exists, skip")
            return
        path.write_bytes(resp.content)
    except Exception as e:
        traceback.print_exc()
        typer.echo(f"fetch {url} error: {type(e)} {e}")
        return


def fetch_image(url: str, prefix: str) -> None:
    return fetch_media(url, prefix=prefix)


def fetch_video(url: str, prefix: str) -> None:
    return fetch_media(url, prefix=prefix)


@cmd.command()
def download(
    file: Path = typer.Argument(..., help='日志文件路径'),
    downlaod_prefix: str = typer.Option('stash-tool-http-capture'),
):
    """下载图片和视频"""
    image_urls = []
    video_urls = []
    for line in parse_log(file):
        if not line:
            continue

        body = Body(**line)
        if 'image' in body.response.headers.get('Content-Type', ''):
            image_urls.append(body.request.url)
        if 'video' in body.response.headers.get('Content-Type', ''):
            video_urls.append(body.request.url)

    with ThreadPoolExecutor() as executor:
        for url in image_urls:
            executor.submit(fetch_image, url, f"{downlaod_prefix}/image")

        for url in video_urls:
            executor.submit(fetch_video, url, f"{downlaod_prefix}/video")

        executor.shutdown(wait=True)


@cmd.command()
def urls(
    file: Path = typer.Argument(..., help='日志文件路径'),
    dest: Path = typer.Option('-', '--dest', help='结果输出路径, 默认标准输出'),
    uniq: bool = typer.Option(True, '--uniq', help='去重'),
    sort: bool = typer.Option(True, '--sort', help='对结果排序'),
):
    """返回所有请求的 URL"""
    urls = [line['request']['url'] for line in parse_log(file) if line]

    hosts = []
    for url in urls:
        result = re.match('https?://([^/]*)/(.*)?', url)
        if result:
            hosts.append(result.groups()[0])

    if uniq:
        urls = list(set(urls))

    if sort:
        urls.sort()

    if str(dest) == '-':
        for url in urls:
            print(url)

    if not dest.exists() or dest.is_file():
        dest.write_text('\n'.join(urls))


if __name__ == '__main__':
    cmd()
