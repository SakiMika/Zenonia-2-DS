"""python test_preparegame.py [GAME.zip|GAME.jar]
Without a fixture: security/name/EN restore tests only. Standard library only.
No NDS hardware, renderer/font or gameplay claims.
"""
import importlib.util,io,json,os,shutil,struct,sys,tempfile,unittest,zipfile
from pathlib import Path
fixture=Path(sys.argv.pop(1)).resolve() if len(sys.argv)>1 else None
spec=importlib.util.spec_from_file_location('pg',Path(__file__).with_name('preparegame.py'));pg=importlib.util.module_from_spec(spec);spec.loader.exec_module(pg)
def archive(entries):
 f=io.BytesIO()
 with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in entries:z.writestr(n,b)
 return f.getvalue()
class FolderArchive:
 def __init__(self,path):self.path=Path(path)
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return (self.path/n).read_bytes()
 def namelist(self):return [p.relative_to(self.path).as_posix() for p in self.path.rglob('*') if p.is_file() and p.name!='runner.json']
def prepare(project,language,offline=True):
 project.select(language,offline);return project.create_game_folder()
def hashes(folder):return {p.relative_to(folder).as_posix():pg.sha(p.read_bytes()) for p in Path(folder).rglob('*') if p.is_file()}
def edit_record(folder,entry,index,text):
 path=folder/entry['txt'];rs=pg.read_direct_txt(path);rs[index]['text']=text
 pg.write_direct_txt(path,['path='+entry['path'],'type='+entry['type'],'encoding=cp949'],rs)

class SafetyTests(unittest.TestCase):
 def test_names(self):
  self.assertEqual(pg.package_name('vi'),'VI')
  for bad in ['../x','CON','nul','COM1','EN','KR','VI/EN','','A'*25,'1VI']:
   with self.assertRaises(ValueError):pg.package_name(bad)
 def test_archive_paths(self):
  for name in ['../escape','/absolute','a\\b','C:x']:
   with self.assertRaises(ValueError):pg.decode_game_archive(archive([(name,b'x')]))
  with self.assertRaises(ValueError):pg.decode_game_archive(archive([('a//b',b'x'),('a/b',b'x')]))
 def test_symlink(self):
  f=io.BytesIO()
  with zipfile.ZipFile(f,'w') as z:
   i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=0o120777<<16;z.writestr(i,'/etc/passwd')
  with self.assertRaises(ValueError):pg.decode_game_archive(f.getvalue())
 def test_java_only(self):
  with self.assertRaises(ValueError):pg.decode_game_archive(archive([('Main.class',b'java')]))
 def test_zt1_bounded(self):
  import zlib
  body=zlib.compress(b'X'*1000)
  for size in [1,17*1024*1024]:
   with self.assertRaises(ValueError):pg.zt1_decompress(struct.pack('<II',len(body)+8,size)+body)
 def test_restore_en_not_overwrite(self):
  with tempfile.TemporaryDirectory() as t:
   p=pg.PrepareProject(t);m=pg.read_manifest(p.en)
   self.assertEqual(len(m['files']),56)
   self.assertEqual(sum(e['records'] for e in m['files']),10423)
   marker=p.en/'keep_user_edit.txt';marker.write_text('keep','utf-8');pg.PrepareProject(t)
   self.assertEqual(marker.read_text(),'keep')

@unittest.skipUnless(fixture and fixture.is_file(),'Pass a native game ZIP/JAR fixture')
class PackageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.project=pg.PrepareProject(cls.tmp.name)
  cls.input=fixture.read_bytes();cls.input_sha=pg.sha(cls.input)
  cls.jar,cls.assets,choices=pg.decode_game_archive(cls.input);assert not choices
  state=cls.project.open(cls.input,fixture.name);assert state['selected']=='EN' and state['output'] is None,state;assert not cls.project.game_target.exists();cls.project.create_game_folder()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_01_direct_and_nested(self):
  for data in [self.jar,archive([('sub/game.jar',self.jar),('app_info',b'PRIVATE')])]:
   jar,assets,choices=pg.decode_game_archive(data);self.assertEqual(jar,self.jar);self.assertEqual(assets,self.assets);self.assertFalse(choices)
  data=archive([('one.jar',self.jar),('two.jar',self.jar)])
  self.assertEqual(pg.decode_game_archive(data)[2],['one.jar','two.jar'])
  self.assertEqual(pg.decode_game_archive(data,'two.jar')[0],self.jar)
 def test_02_kr_exact_and_no_private_wrapper(self):
  p=self.project;s=prepare(p,'KR',False)
  expected={n:b for n,b in self.assets.items() if not n.upper().startswith('META-INF/')}
  with FolderArchive(s['output']['game_directory']) as z:self.assertEqual({n:z.read(n) for n in z.namelist()},expected)
  self.assertEqual(pg.sha(fixture.read_bytes()),self.input_sha)
  self.assertEqual((p.project/'original.jar').read_bytes(),self.jar)
  self.assertEqual(p.game_target,p.home/'zenonia2nds')
  self.assertFalse(any(p.project.glob('card/**/*.jar')))
  self.assertFalse(any(p.project.glob('card/**/*.zip')))
  self.assertNotIn('jar',s['output']);self.assertNotIn('zip',s['output'])
  self.assertEqual(hashes(p.game_target),hashes(s['output']['prepared_game_directory']))
 def test_03_english_text_and_unchanged_nontext(self):
  p=self.project;s=prepare(p,'EN',False);changed=0
  with FolderArchive(s['output']['game_directory']) as z:
   for n,b in self.assets.items():
    if n.upper().startswith('META-INF/'):continue
    if n not in pg.text_assets(self.assets):self.assertEqual(z.read(n),b)
    if n.endswith('.zt1') and pg.zt1_decompress(b)[:4]==b'GXL\1':self.assertEqual(pg.gxl_fingerprint(pg.zt1_decompress(z.read(n))),pg.gxl_fingerprint(pg.zt1_decompress(b)))
    if z.read(n)!=b:changed+=1
  self.assertGreater(changed,30)
  en=pg.read_manifest(p.en);item=next(e for e in en['files'] if e['path']=='data/XlsItem.zt1')
  self.assertIn('Wooden Sword',[r['text'] for r in pg.read_direct_txt(p.en/item['txt'])])
 def test_04_clone_en_and_dump_kr(self):
  p=self.project;prepare(p,'EN',True);s=p.create('VI','EN');self.assertIn('VI',s['languages'])
  vi=p.language_dir('VI')
  for f in p.en.rglob('*.txt'):self.assertEqual(f.read_bytes(),(vi/f.relative_to(p.en)).read_bytes())
  self.assertEqual(json.loads((vi/'_package.json').read_text())['name'],'VI')
  p.create('KO_COPY','KR');ko=p.language_dir('KO_COPY')
  for f in (p.project/'kr_original').rglob('*.txt'):self.assertEqual(f.read_bytes(),(ko/f.relative_to(p.project/'kr_original')).read_bytes())
  with self.assertRaises(ValueError):p.create('VI','EN')
 def test_05_edit_clone_then_select_auto_inject(self):
  p=self.project;vi=p.language_dir('VI');m=pg.read_manifest(vi);entry=next(e for e in m['files'] if e['path']=='data/XlsItem.zt1')
  before=(p.en/entry['txt']).read_bytes();rs=pg.read_direct_txt(vi/entry['txt']);i=next(r['index'] for r in rs if r['text']=='Wooden Sword')
  edit_record(vi,entry,i,'Test Sword');s=prepare(p,'VI',True)
  with FolderArchive(s['output']['game_directory']) as z:
   _,records=pg.resource_records(entry['path'],z.read(entry['path']));self.assertEqual(records[i]['src'],'Test Sword')
  self.assertEqual((p.en/entry['txt']).read_bytes(),before)
 def test_06_en_edits_reload_and_invalid_output_atomic(self):
  p=self.project;m=pg.read_manifest(p.en);entry=next(e for e in m['files'] if e['path']=='data/StrHelp.zt1');path=p.en/entry['txt'];backup=path.read_bytes()
  try:
   rs=pg.read_direct_txt(path);text=rs[0]['text'].replace('Move','Walk',1);self.assertNotEqual(text,rs[0]['text']);edit_record(p.en,entry,0,text)
   s=prepare(p,'EN',True)
   with FolderArchive(s['output']['game_directory']) as z:self.assertEqual(pg.resource_records(entry['path'],z.read(entry['path']))[1][0]['src'],text)
  finally:path.write_bytes(backup)
  s=prepare(p,'EN',True);output=Path(s['output']['prepared_game_directory']);digest=hashes(output);deployed=hashes(p.game_target)
  native=next(e for e in m['files'] if e['path']=='binary.mod');path=p.en/native['txt'];backup=path.read_bytes()
  try:
   rs=pg.read_direct_txt(path);i=0;edit_record(p.en,native,i,'X'*(rs[i]['max_len']+1))
   with self.assertRaises(ValueError):prepare(p,'EN',True)
   self.assertEqual(hashes(output),digest);self.assertEqual(hashes(p.game_target),deployed)
  finally:path.write_bytes(backup)
 def test_065_select_deploy_failure_keeps_both_folders(self):
  from unittest.mock import patch
  p=self.project;s=prepare(p,'EN',True);before=hashes(p.game_target);prepared=Path(s['output']['prepared_game_directory']);old=hashes(prepared);state=p.state()
  with patch.object(pg,'deploy_game_directory',side_effect=PermissionError('card is read-only')):
   with self.assertRaises(PermissionError):prepare(p,'EN',True)
  self.assertEqual(hashes(p.game_target),before);self.assertEqual(hashes(prepared),old)
  self.assertEqual(p.state()['output'],state['output']);self.assertEqual(p.state()['offline'],state['offline'])
 def test_07_offline_profile_guard(self):
  out,status=pg.apply_offline_profile(self.assets);off=0x34+0x5a4b4-0x1000
  self.assertEqual(out['binary.mod'][off:off+2],bytes.fromhex('0220'))
  self.assertEqual(out['binary.mod'][:off],self.assets['binary.mod'][:off]);self.assertEqual(out['binary.mod'][off+2:],self.assets['binary.mod'][off+2:])
  bad=dict(self.assets);b=bytearray(bad['binary.mod']);b[0x100]^=1;bad['binary.mod']=bytes(b)
  with self.assertRaises(ValueError):pg.apply_offline_profile(bad)
 def test_08_dynamic_color_preserved(self):
  p=self.project;s=prepare(p,'EN',True)
  with FolderArchive(s['output']['game_directory']) as z:
   typ,recs=pg.resource_records('binary.mod',z.read('binary.mod'));self.assertIn(' !c%s%s%s Find !N',[r['src'] for r in recs])

class DeploymentTests(unittest.TestCase):
 def setup_payload(self,root):
  payload=root/'payload';payload.mkdir();(payload/'binary.mod').write_bytes(b'unit-test-module');(payload/'data').mkdir();(payload/'data/table').write_bytes(b'unit-test-data')
  target=root/'zenonia2nds';target.mkdir();(target/'old-only').write_bytes(b'backup-me')
  (root/'source').mkdir();header=root/'source/runner_package_config.h';header.write_text('#pragma once\n#define RUNNER_ASSET_COUNT 0u\n#define RUNNER_ASSET_BYTES 0u\n')
  return payload,target,header
 def test_deploy_directory_backup_no_source_edits(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);payload,target,header=self.setup_payload(root)
   before=header.read_bytes();save=root/'ZKR1.sav';save.write_bytes(b'keep-save');result=pg.deploy_game_directory(payload,target,root)
   self.assertEqual((target/'binary.mod').read_bytes(),(payload/'binary.mod').read_bytes());self.assertFalse((target/'old-only').exists())
   self.assertEqual((Path(result['backup'])/'old-only').read_bytes(),b'backup-me')
   self.assertEqual(header.read_bytes(),before);self.assertEqual(save.read_bytes(),b'keep-save')
   self.assertFalse(pg.deploy_game_directory(payload,target,root)['changed'])
 def test_copy_failure_rolls_back_root(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);payload,target,header=self.setup_payload(root);before=header.read_bytes()
   real_replace=pg.os.replace
   def fail_install(src,dst):
    if Path(src).name=='new' and Path(dst)==target:raise PermissionError('test commit failure')
    return real_replace(src,dst)
   with patch.object(pg.os,'replace',side_effect=fail_install):
    with self.assertRaises(PermissionError):pg.deploy_game_directory(payload,target,root)
   self.assertEqual((target/'old-only').read_bytes(),b'backup-me');self.assertFalse((target/'binary.mod').exists());self.assertEqual(header.read_bytes(),before)
 def test_target_discovery_root_and_tools(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'source').mkdir();(root/'source/main.cpp').write_text('');(root/'Makefile').write_text('');(root/'tools').mkdir()
   self.assertEqual(pg.default_game_target(root),root/'zenonia2nds');self.assertEqual(pg.default_game_target(root/'tools'),root/'zenonia2nds')
 def test_bad_target_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for target in [root,root/'games/p/zenonia2nds',root/'en/zenonia2nds',root/'wrong-name']:
    with self.assertRaises(ValueError):pg.validate_game_target(target,root)

class ExtraDirectoryTests(unittest.TestCase):
 def test_card_root_folder_is_exact(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'card').mkdir();p=pg.PrepareProject(r/'tool',r/'card/zenonia2nds')
   self.assertEqual(p.game_target,r/'card/zenonia2nds')
 def test_no_symlink_target_or_payload(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'real').mkdir();(r/'linked').symlink_to(r/'real',target_is_directory=True)
   with self.assertRaises(ValueError):pg.validate_game_target(r/'linked/zenonia2nds',r/'tool')
   payload=r/'payload';payload.mkdir();(payload/'binary.mod').write_bytes(b'fixture');(payload/'link').symlink_to(r/'real')
   with self.assertRaises(ValueError):pg.deploy_game_directory(payload,r/'zenonia2nds',r/'tool')
 def test_cli_directory_options(self):
  import subprocess
  text=subprocess.check_output([sys.executable,str(Path(pg.__file__)),'--help'],text=True)
  self.assertIn('--card-root',text);self.assertIn('--game-dir',text);self.assertNotIn('--nitrofs',text)

@unittest.skipUnless(fixture and fixture.is_file(),'Pass a native game ZIP/JAR fixture')
class SeparateActionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pg.PrepareProject(self.tmp.name)
  self.p.open(fixture.read_bytes(),fixture.name)
 def tearDown(self):self.tmp.cleanup()
 def test_open_select_and_offline_do_not_create_game(self):
  p=self.p;self.assertFalse(p.game_target.exists());self.assertIsNone(p.last_output)
  p.select('KR',False);p.select('EN',True)
  self.assertFalse(p.game_target.exists());self.assertFalse((p.project/'card').exists())
 def test_check_success_writes_no_game(self):
  p=self.p;s=p.check_errors();self.assertTrue(s['check']['ok']);self.assertEqual(s['check']['checked_files'],56)
  self.assertFalse(p.game_target.exists());self.assertFalse((p.project/'card').exists());self.assertFalse((p.home/'error.txt').exists())
 def test_check_collects_errors_preserves_output_and_clears_after_fix(self):
  p=self.p;p.create_game_folder();old=hashes(p.game_target);m=pg.read_manifest(p.en)
  files=[p.en/m['files'][i]['txt'] for i in [0,1]];before=[f.read_bytes() for f in files]
  try:
   for f in files:f.write_text('invalid record format',encoding='utf-8')
   # Removing records is always invalid, even for reference-only resources.
   s=p.check_errors();self.assertFalse(s['check']['ok']);self.assertGreaterEqual(len(s['check']['errors']),2)
   log=p.home/'error.txt';self.assertTrue(log.is_file());text=log.read_text('utf-8')
   for i in [0,1]:self.assertIn(m['files'][i]['path'],text)
   self.assertEqual(hashes(p.game_target),old)
   with self.assertRaises(ValueError):p.create_game_folder()
   self.assertEqual(hashes(p.game_target),old)
  finally:
   for f,b in zip(files,before):f.write_bytes(b)
  self.assertTrue(p.check_errors()['check']['ok']);self.assertFalse((p.home/'error.txt').exists())
 def test_kr_skips_translation_for_check_and_creation(self):
  from unittest.mock import patch
  p=self.p;p.select('KR',False)
  shutil.rmtree(p.project/'kr_original')
  with patch.object(pg,'validate_translation',side_effect=AssertionError('KR must not validate')):
   s=p.check_errors();self.assertTrue(s['check']['skipped']);self.assertFalse(p.game_target.exists())
   s=p.create_game_folder()
  for n,b in p.assets.items():
   if not n.upper().startswith('META-INF/'):self.assertEqual((p.game_target/n).read_bytes(),b)
 def test_error_log_for_missing_txt(self):
  p=self.p;m=pg.read_manifest(p.en);f=p.en/m['files'][0]['txt'];f.unlink()
  s=p.check_errors();self.assertFalse(s['check']['ok']);self.assertIn(m['files'][0]['path'],(p.home/'error.txt').read_text())
 def test_check_existing_output_does_not_touch_folder(self):
  p=self.p;p.create_game_folder();old=hashes(p.game_target);stamp=p.game_target.stat().st_mtime_ns
  p.check_errors();self.assertEqual(hashes(p.game_target),old);self.assertEqual(p.game_target.stat().st_mtime_ns,stamp)
 def test_error_report_symlink_refused(self):
  p=self.p;other=p.home/'original-log';other.write_text('keep');(p.home/'error.txt').symlink_to(other)
  m=pg.read_manifest(p.en);(p.en/m['files'][0]['txt']).unlink()
  with self.assertRaises(ValueError):p.check_errors()
  self.assertEqual(other.read_text(),'keep')

class EnglishUiTests(unittest.TestCase):
 def test_english_ui_and_separate_actions(self):
  self.assertIn('Check Error',pg.HTML);self.assertIn('Create Game Folder',pg.HTML)
  self.assertIn('<html lang="en">',pg.HTML);self.assertNotIn('Bỏ bước',pg.HTML);self.assertNotIn('đọc lại',pg.HTML)
  self.assertNotIn('không gọi',pg.HTML);self.assertIn("api('check')",pg.HTML);self.assertIn("api('build')",pg.HTML)

if __name__=='__main__':unittest.main(verbosity=2)
