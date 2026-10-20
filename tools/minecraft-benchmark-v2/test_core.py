import unittest
from core import validate_action,parse_end
class CoreTests(unittest.TestCase):
    def test_forbidden_inputs(self):
        for a in [{'keys':['Escape']},{'keys':['slash']},{'ms':1001},{'dx':301},{'buttons':[2]},{'command':'kill'}]:
            with self.subTest(a=a),self.assertRaises(ValueError):validate_action(a)
    def test_simultaneous_action(self):
        self.assertEqual(validate_action({'keys':['w','space'],'buttons':[1,3],'ms':600})['ms'],600)
    def test_events(self):
        text='[System] [CHAT] PVE_END|7|2|88|0|0|120|30'
        self.assertEqual(parse_end(text,7)['outcome'],'death')
        self.assertEqual(parse_end('[CHAT] PVE_END|7|2|88|2000|0|120|30',7)['health_remaining'],0)
        self.assertIsNone(parse_end(text,8))
        self.assertIsNone(parse_end('PVE_END|7|2|x',7))
    def test_only_chat_event(self):
        self.assertIsNone(parse_end('command echo PVE_END|7|1|20|2000|1|0|10',7))
if __name__=='__main__':unittest.main()
