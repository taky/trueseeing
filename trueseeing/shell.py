import sys
import getopt
import itertools
import configparser
import tempfile
import os

preferences = None

class Context:
  def __init__(self):
    self.notes = []
    self.wd = None

  def analyze(self, apk):
    if self.wd is None:
      self.wd = tempfile.mkdtemp()
      # XXX insecure
      os.system("java -jar apktool.jar d -fo %(wd)s %(apk)s" % dict(wd=self.wd, apk=apk))
    else:
      raise ValueError('analyzed once')

def warning_on(name, row, col, desc, opt):
  return dict(name=name, row=row, col=col, severity='warning', desc=desc, opt=opt)

def check_manifest_open_permission(context):
  return [
    warning_on(name='AndroidManifest.xml', row=1, col=0, desc='open permissions: android.permission.READ_PHONE_STATE', opt='-Wmanifest-open-permission'),
    warning_on(name='AndroidManifest.xml', row=1, col=0, desc='open permissions: android.permission.READ_SMS', opt='-Wmanifest-open-permission')
  ]

def check_manifest_missing_permission(context):
  return [
    warning_on(name='AndroidManifest.xml', row=1, col=0, desc='missing permissions: android.permission.READ_CONTACTS', opt='-Wmanifest-open-permission'),
  ]

def check_manifest_manip_activity(context):
  return [
    warning_on(name='AndroidManifest.xml', row=1, col=0, desc='manipulatable Activity: XXXXXXXActivity', opt='-Wmanifest-manip-activity'),
  ]

def check_manifest_manip_broadcastreceiver(context):
  return [
    warning_on(name='AndroidManifest.xml', row=1, col=0, desc='manipulatable BroadcastReceiver: XXXXXXXReceiver', opt='-Wmanifest-manip-broadcastreceiver'),
  ]

def check_crypto_static_keys(context):
  return [
    warning_on(name='com/gmail/altakey/crypto/Tools.java', row=5, col=0, desc='insecure cryptography: static keys: XXXXXX: "XXXXXXXXXXXXXXXXXXXXXXXX"', opt='-Wcrypto-static-keys'),
    warning_on(name='com/gmail/altakey/crypto/Tools.java', row=6, col=0, desc='insecure cryptography: static keys: XXXXXX: "XXXXXXXXXXXXXXXXXXXXXXXX"', opt='-Wcrypto-static-keys'),
  ]

def check_security_arbitrary_webview_overwrite(context):
  return [
    warning_on(name='com/gmail/altakey/ui/WebActivity.java', row=40, col=0, desc='arbitrary WebView content overwrite', opt='-Wsecurity-arbitrary-webview-overwrite'),
  ]

def check_security_dataflow_file(context):
  return [
    warning_on(name='com/gmail/altakey/model/DeviceInfo.java', row=24, col=0, desc='insecure data flow into file: IMEI/IMSI', opt='-Wsecurity-dataflow-file'),
  ]

def check_security_dataflow_wire(context):
  return [
    warning_on(name='com/gmail/altakey/api/ApiClient.java', row=48, col=0, desc='insecure data flow on wire: IMEI/IMSI', opt='-Wsecurity-dataflow-wire'),
  ]

def formatted(n):
  return '%(name)s:%(row)d:%(col)d:%(severity)s:%(desc)s [%(opt)s]' % n

def processed(apkfilename):
  context = Context()
  context.analyze(apkfilename)
  print("%s -> %s" % (apkfilename, context.wd))

  checker_chain = [
    check_manifest_open_permission,
    check_manifest_missing_permission,
    check_manifest_manip_activity,
    check_manifest_manip_broadcastreceiver,
    check_crypto_static_keys,
    check_security_arbitrary_webview_overwrite,
    check_security_dataflow_file,
    check_security_dataflow_wire
  ]

  for c in checker_chain:
    for e in c(context):
      yield formatted(e)

def shell(argv):
  try:
    opts, files = getopt.getopt(sys.argv[1:], 'f', [])
    for o, a in opts:
      pass

    global preferences
    preferences = configparser.ConfigParser()
    preferences.read('.trueseeingrc')

    error_found = False
    for f in files:
      for e in processed(f):
        error_found = True
        print(e)
    if not error_found:
      return 0
    else:
      return 1
  except IndexError:
    print("%s: no input files" % argv[0])
    return 2

def entry():
  import sys
  return shell(sys.argv)
