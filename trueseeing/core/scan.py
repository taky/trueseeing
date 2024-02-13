from __future__ import annotations
from typing import TYPE_CHECKING

from contextlib import contextmanager

if TYPE_CHECKING:
  from typing import List, Optional, Iterator, Dict, Any
  from trueseeing.api import SignatureEntry, SignatureHelper, SignatureMap
  from trueseeing.core.context import Context, ContextType
  from trueseeing.core.android.db import Query
  from trueseeing.core.model.issue import Issue, IssueConfidence

class Scanner:
  _helper: SignatureHelper
  _sigs: Dict[str, SignatureEntry]

  def __init__(self, context: Context, *, sigsels: List[str] = [], excludes: List[str] = [], max_graph_size: Optional[int] = None) -> None:
    from trueseeing.core.config import Configs
    self._context = context
    self._sigs = dict()
    self._excludes = excludes
    self._max_graph_size = max_graph_size
    self._confbag = Configs.get().bag
    self._helper = SignatureHelperImpl(self)

    self._init_sigs(['all'] + sigsels)

  def get_active_signatures(self) -> SignatureMap:
    return self._sigs

  @classmethod
  def get_all_signatures(cls) -> SignatureMap:
    return Scanner(context=None).get_active_signatures()  # type: ignore[arg-type]

  async def scan(self, q: Query) -> int:
    import asyncio
    from pubsub import pub
    from trueseeing.core.exc import InvalidContextError
    from trueseeing.core.android.analysis.flow import DataFlow
    from trueseeing.core.ui import ui
    with DataFlow.apply_max_graph_size(self._max_graph_size):
      with self._apply_excludes_on_context():
        def _detected(issue: Issue) -> None:
          q.issue_raise(issue)

        async def _call(id_: str, ent: SignatureEntry) -> None:
          try:
            await ent['e']()
          except InvalidContextError:
            ui.warn(f'scan: {id_}: context invalid, signature ignored')

        pub.subscribe(_detected, 'issue')
        await asyncio.gather(*[_call(k, v) for k,v in self._sigs.items()])
        pub.unsubscribe(_detected, 'issue')

        return q.issue_count()

  async def clear(self, q: Query) -> None:
    q.issue_clear()

  @contextmanager
  def _apply_excludes_on_context(self) -> Iterator[None]:
    o = self._context.excludes
    self._context.excludes = self._excludes
    yield None
    self._context.excludes = o

  @classmethod
  def _sigsel_matches(cls, sigid: str, sels: List[str]) -> bool:
    def _match(sigid: str, sel: str) -> bool:
      neg = False
      if sel.startswith('no-'):
        sel = sel[3:]
        neg = True
      if sel == 'all':
        return not neg
      elif sel.endswith('-all'):
        psel = sel[:-4]
        return neg ^ sigid.startswith(psel)
      else:
        return neg ^ (sigid == sel)
    o: bool = False
    for x in sels:
      o = _match(sigid, x)
    return o

  def _init_sigs(self, sigsels: List[str]) -> None:
    from itertools import chain
    from trueseeing.sig import discover
    from trueseeing.core.ext import Extension
    for clazz in chain(discover(), Extension.get().get_signatures()):
      matched = False
      t = clazz.create(self._helper)
      for k,v in t.get_sigs().items():
        if self._sigsel_matches(k, sigsels):
          self._sigs[k] = v
          matched = True
      if matched:
        self._confbag.update(t.get_configs())

class SignatureHelperImpl:
  def __init__(self, scanner: Scanner) -> None:
    self._s = scanner
    self._confbag = self._s._confbag
  def get_context(self, typ: Optional[ContextType] = None) -> Any:
    if typ:
      self._s._context.require_type(typ)
    return self._s._context
  def raise_issue(self, issue: Issue) -> None:
    from pubsub import pub
    pub.sendMessage('issue', issue=issue)
  def build_issue(
      self,
      sig_id: str,
      cvss_vector: str,
      confidence: IssueConfidence,
      summary: str,
      description: Optional[str] = None,
      seealso: Optional[str] = None,
      synopsis: Optional[str] = None,
      info1: Optional[str] = None,
      info2: Optional[str] = None,
      info3: Optional[str] = None,
      source: Optional[str] = None,
      row: Optional[str] = None,
      col: Optional[str] = None,
  ) -> Issue:
    from trueseeing.core.model.issue import Issue
    return Issue(
      sig_id=sig_id,
      cvss3_vector=cvss_vector,
      confidence=confidence,
      summary=summary,
      description=description,
      seealso=seealso,
      synopsis=synopsis,
      info1=info1,
      info2=info2,
      info3=info3,
      source=source,
      row=row,
      col=col,
    )
  def get_config(self, k: str) -> Any:
    e = self._confbag[k]
    return e['g']()
  def set_config(self, k: str, v: Any) -> None:
    e = self._confbag[k]
    e['s'](v)
