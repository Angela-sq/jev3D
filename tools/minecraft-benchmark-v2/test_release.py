"""Test fail-safe input release without connecting to the game or VM."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class ReleaseTest(unittest.TestCase):
    def test_failed_button_press_releases_inputs_and_records_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            (Path(tmp)/'minecraft-lab').mkdir()
            spec=importlib.util.spec_from_file_location('guest_trial_test',Path(__file__).with_name('guest_trial.py'))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            d=mod.ROOT/'trial-001';d.mkdir();(mod.ROOT/'current').write_text('1')
            calls=[]
            def fake_run(*args):
                calls.append(args)
                if args==('xdotool','mousedown','1'):
                    raise RuntimeError('injected input error')
            with patch.object(mod,'run',side_effect=fake_run),patch.object(sys,'argv',['guest_trial.py','act','{"keys":["w"],"buttons":[1],"ms":100}']):
                with self.assertRaises(RuntimeError):mod.main()
            self.assertIn(('xdotool','mouseup','1'),calls)
            self.assertIn(('xdotool','mouseup','3'),calls)
            self.assertTrue(any(c[:2]==('xdotool','keyup') and 'w' in c for c in calls))
            event=json.loads((d/'actions.jsonl').read_text())
            self.assertEqual(event['error'],'RuntimeError')
            self.assertGreaterEqual(event['end_ns'],event['start_ns'])

if __name__=='__main__':unittest.main()
