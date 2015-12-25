# * Fingerprinting libraries
# * Fingerprinting obfuscators

import collections
import itertools
import os
import re
from trueseeing.context import warning_on
from trueseeing.smali import OpMatcher, InvocationPattern, DataFlows

def package_name_of(path):
  return os.path.dirname(path).replace('/', '.')

def class_name_of(path):
  return path.replace('.smali', '').replace('/', '.')

def shared_package_of(c1, c2):
  o = []
  try:
    for a,b in zip(c1.split('.'), c2.split('.')):
      if a == b:
        o.append(a)
      else:
        break
  finally:
    return o

def is_kind_of(c1, c2):
  return True if shared_package_of(c1, c2) else False

def package_family_of(p):
  f = collections.OrderedDict([
    (r'javax\..*', None),
    (r'(android\.support\.v[0-9]+)\..*', r'\1'),
    (r'(com\.google\.android\.gms)\..*', r'\1'),
    (r'(.*?)\.internal(?:\..*)?$', r'\1'),
    (r'(.*?)(?:\.[a-z]{,4})+$', r'\1'),
    (r'([a-z0-9_]{5,}(?:\.[a-z0-9_]{2,})+?)\..*', r'\1'),
  ])
  for k, v in f.items():
    if re.match(k, p):
      try:
        return re.sub(k, v, p)
      except TypeError:
        return None
  else:
    return p

def detect_library(context):
  package = context.parsed_manifest().getroot().xpath('/manifest/@package', namespaces=dict(android='http://schemas.android.com/apk/res/android'))[0]

  packages = dict()
  for fn in (context.source_name_of_disassembled_class(r) for r in context.disassembled_classes()):
    family = package_family_of(package_name_of(fn))
    if family is not None:
      try:
        packages[family].append(fn)
      except KeyError:
        packages[family] = [fn]
      else:
        pass
  packages = {k:v for k,v in packages.items() if not is_kind_of(k, package) and re.search(r'\.[a-zA-Z0-9]{4,}(?:\.|$)', k)}

  return [warning_on(name=context.apk, row=1, col=0, desc='detected library: %s (score: %d)' % (p, len(packages[p])), opt='-Wdetect-library') for p in sorted(packages.keys())]

def detect_obfuscators(context):
  return detect_obfuscator_proguard(context)

def detect_obfuscator_proguard(context):
  for c in (class_name_of(context.source_name_of_disassembled_class(r)) for r in context.disassembled_classes()):
    if re.search('(?:^|\.)a$', c):
      return [warning_on(name=context.apk, row=1, col=0, desc='detected obfuscator: ProGuard', opt='-Wdetect-obfuscator')]
  else:
    return []

def detect_url(context):
  class FakeToken:
    def __init__(self, v, p):
      self.v = v
      self.p = p
  
  marks = []
  for cl in context.analyzed_classes():
    # XXX too dumb
    for k in OpMatcher(cl.ops, InvocationPattern('const-string', '.*https?://.+$')).matching():
      marks.append(dict(name=context.class_name_of_dalvik_class_type(cl.qualified_name()), method=k.method_, op=k))
  for name, val in context.string_resources():
    if re.match('https?://.+', val) or re.match('^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:[0-9]+)?$', val) or re.match('^/[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)+', val):
      marks.append(dict(name='resource', method=FakeToken(FakeToken('R.string.%s' % name, []), []), op=FakeToken(None, [None, FakeToken(val, [])])))
      
  for m in marks:
    try:
      m['target_val'] = m['op'].p[1].v
    except (DataFlows.NoSuchValueError):
      pass

  return [warning_on(name=m['name'] + '#' + m['method'].v.v, row=0, col=0, desc='detected URL: %s' % m['target_val'], opt='-Wdetect-url') for m in marks]
