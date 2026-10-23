import unittest
from persistent import transition, expired
class Controls(unittest.TestCase):
 def test_unchanged_holds_not_released(self):
  calls=[];transition({'keys':['w'],'buttons':[3]},{'keys':['w'],'buttons':[3]},lambda *x:calls.append(x))
  self.assertEqual(calls,[])
 def test_replacement_releases_removed_controls(self):
  calls=[];transition({'keys':['w'],'buttons':[3]},{'keys':['a'],'buttons':[]},lambda *x:calls.append(x))
  self.assertIn(('xdotool','keyup','w'),calls);self.assertIn(('xdotool','mouseup','3'),calls);self.assertIn(('xdotool','keydown','a'),calls)
 def test_watchdog(self):
  self.assertFalse(expired({'expires_ns':100},99));self.assertTrue(expired({'expires_ns':100},100));self.assertFalse(expired({},100))
if __name__=='__main__':unittest.main()
