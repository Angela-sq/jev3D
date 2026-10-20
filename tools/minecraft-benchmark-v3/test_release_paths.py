import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
class ReleasePaths(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  home=Path(self.temp.name);(home/'minecraft-lab').mkdir()
  spec=importlib.util.spec_from_file_location('guest_under_test',Path(__file__).with_name('guest_trial.py'));self.m=importlib.util.module_from_spec(spec)
  with patch.object(Path,'home',return_value=home):spec.loader.exec_module(self.m)
  self.d=self.m.ROOT/'trial-001';self.d.mkdir();(self.m.ROOT/'current').write_text('1')
 def test_watchdog_releases_and_clears(self):
  (self.m.ROOT/'held.json').write_text(json.dumps({'keys':['w'],'buttons':[3],'expires_ns':0}))
  with patch.object(self.m,'run') as run:self.m.watchdog(self.d)
  self.assertIn(('xdotool','mouseup','3'),[x.args for x in run.call_args_list]);self.assertEqual(self.m.state(),{})
 def test_hold_survives_between_actions(self):
  held={'keys':['w'],'buttons':[3],'expires_ns':10**30};(self.m.ROOT/'held.json').write_text(json.dumps(held))
  with patch.object(self.m,'run') as run:self.m.watchdog(self.d)
  run.assert_not_called();self.assertEqual(self.m.state(),held)
 def test_input_error_releases(self):
  calls=[]
  def run(*args):
   calls.append(args)
   if args[1]=='mousemove_relative':raise RuntimeError('injected input failure')
  with patch.object(self.m,'run',side_effect=run),patch.object(self.m.sys,'argv',['guest','act','{"keys":["w"],"buttons":[3],"dx":10}']):
   with self.assertRaises(RuntimeError):self.m.main()
  self.assertIn(('xdotool','mouseup','3'),calls);self.assertEqual(self.m.state(),{})
if __name__=='__main__':unittest.main()
