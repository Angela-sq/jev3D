import json,unittest
from collections import Counter
from core import validate_action,parse_end,MOBS
from config import OUT,REPEATS
import analyze,run_trial
class CoreTests(unittest.TestCase):
    def test_forbidden_inputs(self):
        for a in [{'keys':['Escape']},{'keys':['slash']},{'ms':1001},{'dx':301},{'buttons':[2]},{'command':'kill'}]:
            with self.subTest(a=a),self.assertRaises(ValueError):validate_action(a)
    def test_simultaneous_action(self):
        self.assertEqual(validate_action({'keys':['w','space'],'buttons':[1,3],'ms':600})['ms'],600)
    def test_events(self):
        text='[System] [CHAT] PVE_END|7|2|88|0|0|120|30|0|0'
        self.assertEqual(parse_end(text,7)['outcome'],'death')
        self.assertEqual(parse_end('[CHAT] PVE_END|7|2|88|2000|0|120|30|0|0',7)['health_remaining'],0)
        self.assertEqual(parse_end('[CHAT] PVE_END|7|5|88|1500|0|10|30|0|1',7)['outcome'],'target_lost')
        self.assertIsNone(parse_end(text,8))
        self.assertIsNone(parse_end('[CHAT] PVE_END|7|6|88|0|0|120|30|0|0',7))
        self.assertIsNone(parse_end('[CHAT] PVE_END|7|2|88|0|0|120|30',7))
    def test_only_chat_event(self):
        self.assertIsNone(parse_end('command echo PVE_END|7|1|20|2000|1|0|10|0|0',7))
    def test_target_lost_is_a_counted_loss(self):
        s=analyze.summarize([{'outcome':'target_lost','game_seconds':'3','damage_dealt_stat':'0'},{'outcome':'win','game_seconds':'9','damage_dealt_stat':'90'}])
        self.assertEqual((s['valid_trials'],s['win_rate']),(2,.5))
    def test_amendment_replaces_original(self):
        rows=[{'trial_id':'5','outcome':'timeout'},{'trial_id':'205','outcome':'technical'},{'trial_id':'305','outcome':'death'},{'trial_id':'6','outcome':'win'}]
        eff=analyze.effective(rows,{'trials':[{'trial_id':5},{'trial_id':6}]})
        self.assertEqual([r['trial_id'] for r in eff],['305','6'])
    def test_rerun_replaces_technical(self):
        rows=[{'trial_id':'1','outcome':'technical'},{'trial_id':'101','outcome':'death'},{'trial_id':'2','outcome':'win'}]
        eff=analyze.effective(rows,{'trials':[{'trial_id':1},{'trial_id':2},{'trial_id':3}]})
        self.assertEqual([r['trial_id'] for r in eff],['101','2'])
class ScheduleTests(unittest.TestCase):
    def test_balanced(self):
        s=json.loads((OUT/'schedule.json').read_text());t=s['trials']
        self.assertEqual(len(t),len(MOBS)*REPEATS)
        self.assertEqual(Counter(x['mob'] for x in t),Counter({m:REPEATS for m in MOBS}))
        self.assertEqual(sorted(Counter(x['site'] for x in t).values()),[16,17,17])
        for m in MOBS:self.assertEqual(len({x['site'] for x in t if x['mob']==m}),3)
        self.assertEqual([x['trial_id'] for x in t],list(range(1,len(t)+1)))
        self.assertEqual([x['trial_id']-100 for x in s['reruns']],[x['trial_id'] for x in t])
    def test_tie_order(self):
        lines=(OUT/'datapack/data/pve/function/active.mcfunction').read_text().splitlines()
        order=[next(i for i,l in enumerate(lines) if f'end/{o}' in l) for o in ['death','win','target_lost','timeout']]
        self.assertEqual(order,sorted(order))
        self.assertTrue(all('if score #phase pve matches 2' in lines[i] for i in order))
class AuditTests(unittest.TestCase):
    def tool(self,name,inp):return {'type':'assistant','message':{'content':[{'type':'tool_use','name':name,'input':inp}]}}
    def test_audit(self):
        a=str(run_trial.ACTOR);obs=str(OUT/'trials/trial-007/obs-0001.png')
        ok=[self.tool('Bash',{'command':f'python3 {a} begin 7'}),self.tool('Bash',{'command':f"""python3 {a} act '{{"keys":["w"],"ms":500}}'"""}),self.tool('Read',{'file_path':obs})]
        self.assertEqual(run_trial.audit(ok,7),(3,[]))
        bad=[self.tool('Bash',{'command':f'python3 {a} begin 8'}),self.tool('Bash',{'command':'cat events.log'}),self.tool('Read',{'file_path':str(OUT/'trials/trial-007/result.json')})]
        self.assertEqual(len(run_trial.audit(bad,7)[1]),3)
if __name__=='__main__':unittest.main()
