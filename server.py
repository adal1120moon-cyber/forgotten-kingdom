from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, threading, pathlib, os, secrets
root=pathlib.Path(__file__).parent; db=root/'rooms.json'; lock=threading.Lock(); rooms=json.loads(db.read_text()) if db.exists() else {}
class H(BaseHTTPRequestHandler):
 def reply(self,x,status=200):
  b=json.dumps(x,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.end_headers(); self.wfile.write(b)
 def do_GET(self):
  if self.path.startswith('/api/room/'):
   with lock:
    r=rooms.get(self.path.split('/')[-1]); self.reply({k:v for k,v in r.items() if k not in ('key','tokens')} if r else {},200 if r else 404)
  elif self.path in ('/','/index.html'):
   self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write((root/'index.html').read_bytes())
  else:self.send_error(404)
 def do_POST(self):
  try:
   n=int(self.headers['Content-Length']); assert 0<n<1000000; d=json.loads(self.rfile.read(n))
   with lock:
    if self.path=='/api/create':
     code=secrets.token_hex(3); key=secrets.token_hex(16); rooms[code]={'key':key,'tokens':{},'state':d['state'],'rev':0,'chat':[]}; result={'code':code,'key':key}
    else:
     r=rooms[d['code']]; gm=secrets.compare_digest(r['key'],str(d.get('key','')))
     if self.path=='/api/claim':
      i=int(d['i']); assert 0<=i<len(r['state']['characters']); assert str(i) not in r['tokens']; token=secrets.token_hex(16); r['tokens'][str(i)]=token; result={'token':token}
     elif self.path=='/api/save':
      assert gm and r['rev']==d['rev']; r['state']=d['state']; r['rev']+=1; result={'rev':r['rev']}
     else:
      i=int(d.get('i',-1)); assert gm or (str(i) in r['tokens'] and secrets.compare_digest(r['tokens'][str(i)],str(d.get('token','')))); c=r['state']['characters'][i] if not gm else None; name='GM' if gm else c['name']
      if self.path=='/api/action':
       assert not gm; field=d['field']; assert field in ('gear','place'); choices=r['state']['items' if field=='gear' else 'maps']; assert d['value'] in [a[0] for a in choices]; c[field]=d['value']
      elif self.path=='/api/chat':
       msg=str(d['message'])[:500]; r['chat'].append([name,msg]); r['chat']=r['chat'][-100:]
      elif self.path=='/api/roll':
       r['chat'].append([name,'주사위 d20: '+str(secrets.randbelow(20)+1)]); r['chat']=r['chat'][-100:]
      else:raise ValueError()
      r['rev']+=1; result={'rev':r['rev']}
    db.write_text(json.dumps(rooms,ensure_ascii=False)); self.reply(result)
  except Exception:self.reply({'error':'요청 실패: 권한, 접속 또는 변경 충돌을 확인하세요.'},400)
ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8080'))),H).serve_forever()
