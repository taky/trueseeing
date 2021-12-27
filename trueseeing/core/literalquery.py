# -*- coding: utf-8 -*-
# Trueseeing: Non-decompiling Android application vulnerability scanner
# Copyright (C) 2017 Takahiro Yoshimura <takahiro_y@monolithworks.co.jp>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations
from typing import TYPE_CHECKING

import os.path
import pkg_resources

import trueseeing.core
from trueseeing.core.code.op import Op

if TYPE_CHECKING:
  from typing import Any, Iterable, Tuple, Dict, Optional
  from trueseeing.core.store import Store
  from trueseeing.core.flow.code import InvocationPattern

class StorePrep:
  def __init__(self, c: Any) -> None:
    self.c = c

  def stage0(self) -> None:
    with open(pkg_resources.resource_filename(__name__, os.path.join('..', 'libs', 'store.s.sql')), 'r', encoding='utf-8') as f:
      self.c.executescript(f.read())

  def stage1(self) -> None:
    with open(pkg_resources.resource_filename(__name__, os.path.join('..', 'libs', 'store.0.sql')), 'r', encoding='utf-8') as f:
      self.c.executescript(f.read())

  def stage2(self) -> None:
    with open(pkg_resources.resource_filename(__name__, os.path.join('..', 'libs', 'store.1.sql')), 'r', encoding='utf-8') as f:
      self.c.executescript(f.read())


class Query:
  def __init__(self, store: Store) -> None:
    self.db = store.db

  def reversed_insns_in_method(self, from_: Op) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where op in (select op from ops_method where op<(select op from ops_p where p=:from_op) and method=(select method from ops_method where op=(select op from ops_p where p=:from_op))) order by op desc', dict(from_op=from_._id)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  @staticmethod
  def _cond_as_sql(param: Dict[str, Any], t: Optional[str], v: Optional[str]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    cond = dict(cond='1')
    if t is not None or v is not None:
      cond.update(dict(cond=' and '.join(['t=:t' if t is not None else '1', 'v like :v' if v is not None else '1'])))
      param.update({p:q for p,q in dict(t=t, v=v).items() if q is not None})
    return cond, param

  def find_recent_in_method(self, from_: Op, t: str, v: str) -> Iterable[Op]:
    cond, param = self._cond_as_sql(dict(from_op=from_._id), t, v)
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where op in (select op from ops_method where op<=(select op from ops_p where p=:from_op) and method=(select method from ops_method where op=(select op from ops_p where p=:from_op))) and (%(cond)s) order by op desc' % cond, param):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def ops(self) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs'):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def invocations(self, pattern: InvocationPattern) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_invokes join op_vecs using (op) where interests_invokes.v like \'%(insn)s%%\'%(regexp)s' % dict(insn=pattern.insn, regexp=' and target regexp \'%(expr)s\'' % dict(expr=pattern.value))):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def invocations_in_class(self, class_: Op, pattern: InvocationPattern) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_invokes join ops_class using (op) join op_vecs using (op) where class=(select class from ops_class where op=:class_) and interests_invokes.v like \'%(insn)s%%\'%(regexp)s' % dict(insn=pattern.insn, regexp=' and target regexp \'%(expr)s\'' % dict(expr=pattern.value)), dict(class_=class_._id)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def consts(self, pattern: InvocationPattern) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_consts join op_vecs using (op) where interests_consts.v like \'%(insn)s%%\'%(regexp)s' % dict(insn=pattern.insn, regexp=' and target regexp \'%(expr)s\'' % dict(expr=pattern.value))):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def sputs(self, target: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_sputs join op_vecs using (op) where target=:target', dict(target=target)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def iputs(self, target: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_iputs join op_vecs using (op) where target=:target', dict(target=target)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def ops_of(self, insn: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where v=:insn', dict(insn=insn)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def classes_has_method_named(self, pattern: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs join ops_method using (op) where op in (select class from methods_class join method_method_name using (method) where method_name regexp \'%(expr)s\')' % dict(expr=pattern)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def classes_extends_has_method_named(self, method: str, extends: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where op in (select class from classes_extends_name join methods_class using (class) join method_method_name using (method) where method_name regexp \'%(expr1)s\' and extends_name regexp \'%(expr2)s\')' % dict(expr1=method, expr2=extends)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def classes_implements_has_method_named(self, method: str, implements: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where op in (select class from classes_implements_name join methods_class using (class) join method_method_name using (method) where method_name regexp \'%(expr1)s\' and implements_name regexp \'%(expr2)s\')' % dict(expr1=method, expr2=implements)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def qualname_of(self, op: Optional[Op]) -> Optional[str]:
    if op:
      for o, in self.db.execute('select qualname from method_qualname join ops_method using (method) where op=:op', dict(op=op._id)):
        return o # type: ignore[no-any-return]
    return None

  def class_name_of(self, op: Optional[Op]) -> Optional[str]:
    if op:
      for o, in self.db.execute('select class_name from class_class_name join ops_class using (class) where op=:op', dict(op=op._id)):
        return o # type: ignore[no-any-return]
    return None

  def callers_of(self, op: Op) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_invokes join op_vecs using (op) where target=(select qualname from method_qualname where method=(select method from ops_method where op=:op))', dict(op=op._id)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def callers_of_method_named(self, pattern: InvocationPattern) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, op_vecs.v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from interests_invokes join op_vecs using (op) where target regexp \'%(expr)s\'' % dict(expr=pattern)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def methods_in_class(self, method_name: str, related_class_name: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from classes_extends_name left join classes_implements_name using (class) join methods_class using (class) join method_method_name using (method) join op_vecs on (method=op) where (extends_name like :class_pat or implements_name like :class_pat) and method_name like :method_pat', dict(class_pat='%%%s%%' % related_class_name, method_pat='%%%s%%' % method_name)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def related_classes(self, related_class_name: str) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from classes_extends_name left join classes_implements_name using (class) join op_vecs on (class=op) where (extends_name regexp :class_pat or implements_name regexp :class_pat)', dict(class_pat=related_class_name)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def matches_in_method(self, method: Op, pattern: InvocationPattern) -> Iterable[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from ops_method join op_vecs using (op) where method=(select method from ops_method where op=:from_op) and v like \'%(insn)s%%\'%(regexp)s' % dict(insn=pattern.insn, regexp=' and v2 regexp \'%(expr)s\'' % dict(expr=pattern.value)), dict(from_op=method._id)):
      yield Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])

  def class_of_method(self, method: Op) -> Optional[Op]:
    for r in self.db.execute('select op as _0, t as _1, v as _2, op1 as _3, t1 as _4, v1 as _5, op2 as _6, t2 as _7, v2 as _8, op3 as _9, t3 as _10, v3 as _11, op4 as _12, t4 as _13, v4 as _14, op5 as _15, t5 as _16, v5 as _17, op6 as _18, t6 as _19, v6 as _20, op7 as _21, t7 as _22, v7 as _23, op8 as _24, t8 as _25, v8 as _26, op9 as _27, t9 as _28, v9 as _29 from op_vecs where op=(select class from ops_class where op=:from_op)', dict(from_op=method._id)):
      return Op(r[1], r[2], [Op(o[1], o[2], [], id_=o[0]) for o in (r[x:x + 3] for x in range(3, 30, 3)) if o[0] is not None], id_=r[0])
    return None
