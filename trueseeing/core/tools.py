from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
import functools
from contextlib import contextmanager
from trueseeing.core.ui import ui

if TYPE_CHECKING:
  from pathlib import Path
  from typing import Any, Optional, AsyncIterable, TypeVar, List, Iterator, TypedDict, AsyncIterator
  T = TypeVar('T')

  class Toolchain(TypedDict):
    apkeditor: Path
    apksigner: Path
    abe: Path

def noneif(x: Any, defaulter: Any) -> Any:
  if x is not None:
    return x
  else:
    if callable(defaulter):
      return defaulter()
    else:
      return defaulter

async def list_async(iter: AsyncIterable[T]) -> List[T]:
  o = []
  async for t in iter:
    o.append(t)
  return o

def _check_return_code(p: Any, args: Any, out: Any, err: Any) -> None:
  code: int
  if isinstance(p, int):
    code = p
  elif hasattr(p, 'returncode'):
    code = p.returncode
  if code:
    from subprocess import CalledProcessError
    raise CalledProcessError(code, args, out, err)

@functools.lru_cache(maxsize=1)
def require_in_path(cmd: str, cmdline: str) -> None:
  from subprocess import run, CalledProcessError
  try:
    run(cmdline, capture_output=True, check=True, shell=True)
  except CalledProcessError:
    ui.fatal('not found: {cmd}')

async def invoke(as_: str, redir_stderr: bool = False) -> str:
  from subprocess import PIPE, STDOUT
  p = await asyncio.create_subprocess_shell(as_, stdout=PIPE, stderr=(STDOUT if redir_stderr else None))
  out, _ = await p.communicate()
  _check_return_code(p, as_, out, None)
  return out.decode('UTF-8')

async def invoke_passthru(as_: str, nocheck: bool = False) -> None:
  p = await asyncio.create_subprocess_shell(as_)
  await p.communicate()
  if not nocheck:
    _check_return_code(p, as_, None, None)

async def invoke_streaming(as_: str, redir_stderr: bool = False) -> AsyncIterator[bytes]:
  from subprocess import PIPE, STDOUT
  p = await asyncio.create_subprocess_shell(as_, stdout=PIPE, stderr=(STDOUT if redir_stderr else None))
  if p.stdout is not None:
    async for l in p.stdout:
      yield l
  _check_return_code(await p.wait(), as_, None, None)

async def try_invoke(as_: str) -> Optional[str]:
  from subprocess import CalledProcessError
  try:
    return await invoke(as_)
  except CalledProcessError:
    return None

@contextmanager
def toolchains() -> Iterator[Toolchain]:
  from importlib.resources import files, as_file
  require_in_path('java', 'java -version')
  with as_file(files('trueseeing')/'libs'/'apkeditor.jar') as apkeditorpath:
    with as_file(files('trueseeing')/'libs'/'apksigner.jar') as apksignerpath:
      with as_file(files('trueseeing')/'libs'/'abe.jar') as abepath:
        yield dict(
          apkeditor=apkeditorpath,
          apksigner=apksignerpath,
          abe=abepath,
        )

def move_apk(src: str, dest: str) -> None:
  import shutil
  shutil.move(src, dest)
  try:
    shutil.move(src.replace('.apk', '.apk.idsig'), dest.replace('.apk', '.apk.idsig'))
  except OSError:
    pass
