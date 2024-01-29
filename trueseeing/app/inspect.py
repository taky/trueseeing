from __future__ import annotations
from typing import TYPE_CHECKING

from collections import deque
import asyncio
from shlex import shlex
import sys
import re
from trueseeing.core.ui import ui, CoreProgressReporter
from trueseeing.core.exc import FatalError

if TYPE_CHECKING:
  from typing import Mapping, Optional, Any, NoReturn, List, Dict, Awaitable
  from trueseeing.app.shell import Signatures
  from trueseeing.core.context import Context
  from trueseeing.core.model.cmd import Entry, CommandEntry, CommandPatternEntry, OptionEntry, ModifierEntry

class InspectMode:
  def do(
      self,
      target: Optional[str],
      signatures: Signatures,
      batch: bool = False,
      cmdlines: List[str] = [],
  ) -> NoReturn:
    try:
      if ui.is_tty():
        ui.enter_inspect()
      with CoreProgressReporter().scoped():
        self._do(target, signatures, batch, cmdlines)
    finally:
      if ui.is_tty():
        ui.exit_inspect()

  def _do(
      self,
      target: Optional[str],
      signatures: Signatures,
      batch: bool,
      cmdlines: List[str],
  ) -> NoReturn:
    from code import InteractiveConsole

    sein = self
    runner = Runner(signatures, target)

    for line in cmdlines:
      asyncio.run(sein._worker(runner.run(line)))

    if batch:
      sys.exit(0)

    if not ui.is_tty(stdin=True):
      ui.fatal('requires a tty')

    asyncio.run(runner.greeting())

    class LambdaConsole(InteractiveConsole):
      def runsource(self, source: str, filename: Optional[str]=None, symbol: Optional[str]=None) -> bool:
        try:
          asyncio.run(sein._worker(runner.run(source)))
        except FatalError:
          pass
        return False

    try:
      import readline
    except ImportError:
      readline = None # type: ignore[assignment] # noqa: F841
    ps1, ps2 = getattr(sys, 'ps1', None), getattr(sys, 'ps2', None)
    try:
      runner.reset_prompt()
      try:
        LambdaConsole(locals=locals(), filename='<input>').interact(banner='', exitmsg='')
      except QuitSession:
        pass
      sys.exit(0)
    finally:
      sys.ps1, sys.ps2 = ps1, ps2

  async def _worker(self, coro: Any) -> None:
    tasks = [asyncio.create_task(coro)]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
      t.cancel()
    if pending:
      _, _ = await asyncio.wait(pending)
    for t in done:
      if not t.cancelled():
        x = t.exception()
        if x:
          assert isinstance(x, Exception)
          if isinstance(x, QuitSession):
            raise x
          elif not isinstance(x, FatalError):
            ui.fatal('unhandled exception', exc=x)

class QuitSession(Exception):
  pass

class Runner:
  _cmds: Dict[str, CommandEntry]
  _cmdpats: Dict[str, CommandPatternEntry]
  _mods: Dict[str, ModifierEntry]
  _opts: Dict[str, OptionEntry]
  _quiet: bool = False
  _verbose: bool = False
  _target: Optional[str]
  _sigs: Signatures

  def __init__(self, signatures: Signatures, target: Optional[str]) -> None:
    self._sigs = signatures
    self._target = target
    self._cmds = {
      '?':dict(e=self._help, n='?', d='help'),
      '?@?':dict(e=self._help_mod, n='?@?', d='modifier help'),
      '?o?':dict(e=self._help_opt, n='?o?', d='options help'),
      '!':dict(e=self._shell, n='!', d='shell'),
      'o':dict(e=self._set_target, n='o target.apk', d='set target APK'),
      'q':dict(e=self._quit, n='q', d='quit'),
    }
    self._cmdpats = {}
    self._mods = {
      'o':dict(n='@o:option', d='pass option'),
      'gs':dict(n='@gs:<int>[kmKM]', d='set graph size limit'),
    }
    self._opts = {}

    self._init_cmds()

  def _init_cmds(self) -> None:
    from trueseeing.core.ext import Extension
    from trueseeing.core.model.cmd import Command
    from inspect import getmembers, isclass
    from importlib import import_module
    for n in 'alias', 'analyze', 'asm', 'exploit', 'info', 'report', 'search', 'scan', 'show':
      m = import_module(f'trueseeing.app.cmd.{n}')
      for _, clazz in getmembers(m, lambda x: isclass(x) and x != Command and issubclass(x, Command)):
        t = clazz(self)
        self._cmds.update(t.get_commands())
        self._cmdpats.update(t.get_command_patterns())
        self._mods.update(t.get_modifiers())
        self._opts.update(t.get_options())

    for clazz in Extension.get().get_commands():
      t = clazz(self)
      self._cmds.update(t.get_commands())
      self._cmdpats.update(t.get_command_patterns())
      self._mods.update(t.get_modifiers())
      self._opts.update(t.get_options())

  def _get_modifiers(self, args: deque[str]) -> List[str]:
    o = []
    for m in args:
      if m.startswith('@'):
        o.append(m)
    return o

  def _get_effective_options(self, mods: List[str]) -> Mapping[str, str]:
    o = {}
    for m in mods:
      if m.startswith('@o:'):
        for a in m[3:].split(','):
          c: List[str] = a.split('=', maxsplit=1)
          if len(c) == 1:
            o[c[0]] = c[0]
          else:
            o[c[0]] = c[1]
    return o

  def _get_graph_size_limit(self, mods: List[str]) -> Optional[int]:
    for m in mods:
      if m.startswith('@gs:'):
        c = m[4:]
        s = re.search(r'[km]$', c.lower())
        if s:
          return int(m[4:-1]) * dict(k=1024, m=1024*1024)[s.group(0)]
        else:
          return int(m[4:])
    return None

  def get_target(self) -> Optional[str]:
    return self._target

  async def greeting(self) -> None:
    from trueseeing import __version__ as version
    ui.success(f"Trueseeing {version}")

  async def run(self, s: str) -> None:
    try:
      await self._run(s)
    finally:
      self._reset_loglevel()
      self.reset_prompt()

  async def _run(self, s: str) -> None:
    if not await self._run_raw(s):
      o: deque[str] = deque()
      lex = shlex(s, posix=True, punctuation_chars=';=')
      lex.wordchars += '@:,!$'
      for t in lex:
        if re.fullmatch(';+', t):
          if not await self._run_cmd(o, line=None):
            ui.error('invalid command, type ? for help')
          o.clear()
        else:
          o.append(t)
      if o:
        if not await self._run_cmd(o, line=s):
          ui.error('invalid command, type ? for help')

  async def _run_raw(self, line: str) -> bool:
    ent: Any = None
    for pat in [k for k,v in self._cmdpats.items() if v.get('raw')]:
      m = re.match(pat, line)
      if m:
        ent = self._cmdpats[pat]
        if m.end() < (len(line) - 1):
          ui.warn('ignoring trailer: {}'.format(line[m.end():]))
        break
    if ent is None:
      return False
    else:
      assert m is not None
      await self._as_cmd(ent['e'](line=m.group(0)))
      return True

  async def _run_cmd(self, tokens: deque[str], line: Optional[str]) -> bool:
    ent: Any = None
    if line is not None:
      for pat in [k for k,v in self._cmdpats.items() if not v.get('raw')]:
        m = re.match(pat, line)
        if m:
          ent = self._cmdpats[pat]
          break

    if ent is None:
      c = tokens[0]
      if c in self._cmds:
        ent = self._cmds[c]

    if ent is None:
      return False
    else:
      await self._as_cmd(ent['e'](args=tokens))
      return True

  async def _as_cmd(self, coro: Awaitable[Any]) -> None:
    try:
      try:
        await coro
      except KeyboardInterrupt:
        ui.fatal('interrupted')
    except FatalError:
      pass

  def _reset_loglevel(self, debug:bool = False) -> None:
    ui.set_level(ui.INFO)

  def reset_prompt(self) -> None:
    if self._target:
      sys.ps1, sys.ps2 = ui.colored(f'ts[{self.get_target()}]> ', color='yellow'), ui.colored('... ', color='yellow')
    else:
      sys.ps1, sys.ps2 = ui.colored('ts> ', color='yellow'), ui.colored('... ', color='yellow')

  async def _help(self, args: deque[str]) -> None:
    ents: Dict[str, CommandEntry] = dict()
    ents.update(self._cmds)
    ents.update(self._cmdpats)
    await self._help_on('Commands:', ents)

  async def _help_mod(self, args: deque[str]) -> None:
    await self._help_on('Modifiers:', self._mods)

  async def _help_opt(self, args: deque[str]) -> None:
    await self._help_on('Options:', self._opts)

  async def _help_on(self, topic: str, entries: Dict[str, Entry]) -> None:
    ui.success(topic)
    width = (2 + max([len(e.get('d', '')) for e in entries.values()]) // 4) * 4
    for k in sorted(entries):
      e = entries[k]
      if 'n' in e:
        ui.stderr(
          f'{{n:<{width}s}}{{d}}'.format(n=e['n'], d=e['d'])
        )

  def _require_target(self, msg: Optional[str] = None) -> None:
    if self._target is None:
      ui.fatal(msg if msg else 'need target')

  def _get_context(self, path: str) -> Context:
    from trueseeing.core.context import Context
    return Context(path, [])

  async def _get_context_analyzed(self, path: str, level: int = 3) -> Context:
    c = self._get_context(path)
    await c.analyze(level=level)
    return c

  async def _shell(self, args: deque[str]) -> None:
    from trueseeing.core.env import get_shell
    from asyncio import create_subprocess_exec
    await (await create_subprocess_exec(get_shell())).wait()

  def _decode_analysis_level(self, level: int) -> str:
    analysislevelmap = {0:'no', 1: 'minimally', 2: 'lightly', 3:'fully'}
    return analysislevelmap.get(level, '?')

  async def _quit(self, args: deque[str]) -> None:
    raise QuitSession()

  async def _set_target(self, args: deque[str]) -> None:
    _ = args.popleft()

    if not args:
      ui.fatal('need path')

    self._target = args.popleft()
