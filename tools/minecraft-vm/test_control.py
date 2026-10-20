import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import control

class ControlTests(unittest.TestCase):
    def test_rejects_unbounded_input(self):
        for args in [('key','w','1001'), ('key','w','-1'), ('look','301','0'),
                     ('point','1280','0'), ('click','2','50')]:
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit): control.parser().parse_args(args)

    def test_key_released_when_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(control,'ROOT',Path(tmp)), \
             patch('sys.argv',['control.py','key','w','100']), \
             patch.object(control,'run') as run, \
             patch.object(control.time,'sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): control.main()
            self.assertEqual(run.call_args_list[-1].args,('xdotool','keyup','w'))

    def test_mouse_released_when_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(control,'ROOT',Path(tmp)), \
             patch('sys.argv',['control.py','click','1','100']), \
             patch.object(control,'run') as run, \
             patch.object(control.time,'sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): control.main()
            self.assertEqual(run.call_args_list[-1].args,('xdotool','mouseup','1'))

if __name__ == '__main__': unittest.main()
