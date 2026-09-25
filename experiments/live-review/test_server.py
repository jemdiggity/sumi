import importlib.util,json,tempfile,unittest,os
from pathlib import Path
spec=importlib.util.spec_from_file_location('live_server',Path(__file__).with_name('server.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.args=(self.root/'runtime',Path(__file__).with_name('bebop.html'),self.root/'bundle.js',self.root/'registry',Path(os.environ['SUMI_DOM_MODULE']),2);self.pool=mod.Pool(*self.args)
 def tearDown(self):self.pool.close();self.pool.db.close();self.tmp.cleanup()
 def payload(self,text='Make it quieter'):
  return {'revision':self.pool.getmeta('current'),'annotation':{'id':'a','comment':text,'elementPath':'h1'},'scene':{'search':'Jet','filter':'crew'}}
 def test_idempotency_and_edited_snapshot(self):
  payload=self.payload();job=self.pool.submit(payload);self.assertEqual(job,self.pool.submit(payload));other=self.pool.submit(self.payload('Change the title'));self.assertNotEqual(job,other);self.assertEqual(len(self.pool.state()['jobs']),2)
 def test_restart_preserves_queue_and_marks_interrupted(self):
  job=self.pool.submit(self.payload());self.pool.update(job,'working');self.pool.setmeta('paused','true');self.pool.close();self.pool.db.close();self.pool=mod.Pool(*self.args);self.assertTrue(self.pool.state()['paused']);self.assertEqual(self.pool.state()['jobs'][0]['status'],'interrupted')
 def test_reject_unknown_revision_and_empty_comment(self):
  p=self.payload();p['revision']='nope'
  with self.assertRaises(ValueError):self.pool.submit(p)
  with self.assertRaises(ValueError):self.pool.submit(self.payload('  '))
 def test_clean_candidate_is_published(self):
  initial=self.pool.getmeta('current');job=self.pool.submit(self.payload());row=self.pool.db.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
  def good(ws,*_):
   p=ws/'index.html';p.write_text(p.read_text().replace('</footer>','<small>Queue test</small></footer>'));return 'Small footer change'
  self.pool.model=good;self.pool.execute(row);self.assertNotEqual(self.pool.getmeta('current'),initial);self.assertEqual(self.pool.state()['jobs'][0]['status'],'published');self.assertFalse(self.pool.conflicts(self.pool.root/'workspaces'/('merge-'+job)))
 def test_overlapping_changes_use_reconciliation(self):
  base=self.args[1].read_text();payload=self.payload('First title tweak');first=self.pool.submit(payload);payload['annotation']['id']='second';payload['annotation']['comment']='Second title tweak';second=self.pool.submit(payload);phases=[]
  def model(ws,prompt,job,phase):
   phases.append(phase)
   text=base.replace('<title>','<title>'+('A B ' if phase=='reconcile' else 'A ' if job==first else 'B '))
   (ws/'index.html').write_text(text);return 'Title changed'
  self.pool.model=model
  for job in [first,second]:self.pool.execute(self.pool.db.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone())
  self.assertIn('reconcile',phases);self.assertTrue(all(j['status']=='published' for j in self.pool.state()['jobs']));self.assertIn('<title>A B ',self.pool.revision(self.pool.getmeta('current'))['html'])
 def test_bad_worker_preserves_published_revision(self):
  initial=self.pool.getmeta('current');job=self.pool.submit(self.payload());row=self.pool.db.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
  def broken(ws,*_):
   (ws/'index.html').write_text('<html><body><script>broken(</script></body></html>');return 'bad test candidate'
  self.pool.model=broken;self.pool.execute(row);self.assertEqual(self.pool.getmeta('current'),initial);self.assertEqual(self.pool.state()['jobs'][0]['status'],'failed')
if __name__=='__main__':unittest.main()
