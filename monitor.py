#!/usr/bin/env python3
from __future__ import annotations
import json, os, smtplib, ssl, sys
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Iterable
import requests

BASE_URL='https://www.recreation.gov'
CONFIG_PATH=Path('watches.json')
STATE_PATH=Path('state.json')
TIMEOUT_SECONDS=20

TOUR_NAMES={
 '92':'Broadway Tour','93':'Historic Tour','94':'Trog Tour','95':'Introduction to Caving Tour',
 '96':'Wild Cave Tour','98':'Domes and Dripstones Tour','99':'Great Onyx Lantern Tour',
 '100':'Grand Avenue Tour','105':'River Styx Tour','106':'Frozen Niagara Tour',
 '107':'Mammoth Passage Tour','108':'Discovery Tour [Self-Guided]','115':'Gothic Avenue Tour',
 '185':'Cleaveland Avenue Tour','219':'Accessible Tour','1012':'Extended Historic Tour',
 '10088885':'Wondering Woods Tours'
}

def daterange(start:str,end:str)->Iterable[str]:
 s=date.fromisoformat(start); e=date.fromisoformat(end)
 while s<=e: yield s.isoformat(); s+=timedelta(days=1)

def count(v:Any)->int:
 if isinstance(v,dict):
  for k in ('ANY','FIT','COMM','WALKUP','LOTTERY'):
   if isinstance(v.get(k),(int,float)): return int(v[k])
 return int(v) if isinstance(v,(int,float)) else 0

def extract(payload:Any)->list[dict[str,Any]]:
 raw=payload if isinstance(payload,list) else []
 if isinstance(payload,dict):
  for k in ('availability','slots','tour_availability','data'):
   if isinstance(payload.get(k),list): raw=payload[k]; break
  else: raw=[v for v in payload.values() if isinstance(v,dict)]
 out=[]
 for s in raw:
  if not isinstance(s,dict): continue
  inv=count(s.get('inventory_count')); res=count(s.get('reservation_count'))
  tid=str(s.get('tour_id') or s.get('tourId') or s.get('id') or '')
  tm=str(s.get('tour_time') or s.get('tourTime') or s.get('time') or s.get('start_time') or s.get('startTime') or 'Unknown time')
  out.append({'tour_id':tid,'tour_name':TOUR_NAMES.get(tid, f'Tour {tid}'),'tour_time':tm,'available':max(inv-res,0)})
 return out

def check_date(session,facility,day):
 for endpoint in ('ticket','timedentry'):
  u=f'{BASE_URL}/api/{endpoint}/availability/facility/{facility}'
  r=session.get(u,params={'date':day},timeout=TIMEOUT_SECONDS); r.raise_for_status(); p=r.json(); slots=extract(p)
  if slots: return slots
  if p not in ([],{},None): return slots
 return []

def send_email(subject:str, body:str)->bool:
 host=os.getenv('SMTP_HOST','smtp.gmail.com'); port=int(os.getenv('SMTP_PORT','465'))
 user=os.getenv('SMTP_USERNAME'); password=os.getenv('SMTP_PASSWORD'); to=os.getenv('ALERT_TO')
 if not all((user,password,to)):
  print('Email not configured; skipping send.'); return False
 msg=EmailMessage(); msg['Subject']=subject; msg['From']=user; msg['To']=to; msg.set_content(body)
 with smtplib.SMTP_SSL(host,port,context=ssl.create_default_context()) as smtp:
  smtp.login(user,password); smtp.send_message(msg)
 print(f'Email sent to {to}'); return True

def main()->int:
 cfg=json.loads(CONFIG_PATH.read_text()); old={}
 # Accept both the original single-watch watches.json format and the newer {"watches": [...]} format.
 watches = cfg.get('watches') if isinstance(cfg, dict) else None
 if not isinstance(watches, list):
  watches = [cfg] if isinstance(cfg, dict) and cfg.get('facility_id') else []
 if STATE_PATH.exists():
  try: old=json.loads(STATE_PATH.read_text())
  except Exception: old={}
 session=requests.Session(); session.headers.update({'User-Agent':'TourWatch/0.3 (+https://github.com/TourWatch/tourwatch; read-only availability checker)','Accept':'application/json'})
 current={}; details={}
 print('TourWatch V3:',datetime.now().astimezone().isoformat(timespec='seconds'))
 for wi,w in enumerate(watches):
  facility=str(w['facility_id']); party=int(w.get('party_size',1)); needle=str(w.get('tour_name_contains','')).lower().strip()
  for day in daterange(w['start_date'],w.get('end_date',w['start_date'])):
   for s in check_date(session,facility,day):
    hay=f"{s['tour_name']} {s['tour_id']}".lower()
    if needle and needle not in hay: continue
    if s['available']<party: continue
    key=f"{facility}|{day}|{s['tour_id']}|{s['tour_time']}|party{party}"
    current[key]=s['available']; details[key]=(w.get('name','TourWatch'),day,s)

 old_keys=set(old.get('available',{})); new_keys=set(current)-old_keys
 first_run=not STATE_PATH.exists() or not old.get('initialized')
 print(f'Qualifying slots now: {len(current)} | newly opened since last run: {0 if first_run else len(new_keys)}')
 for k in sorted(new_keys if not first_run else []):
  name,day,s=details[k]
  print(f"NEW: {s['tour_name']} | {day} | {s['tour_time']} | {s['available']} seats")

 if first_run:
  print('Baseline created. Existing availability will NOT trigger alerts.')
 elif new_keys:
  lines=[]
  for k in sorted(new_keys):
   name,day,s=details[k]
   link=f"https://www.recreation.gov/ticket/234640/ticket/{s['tour_id']}"
   lines.append(f"{s['tour_name']}\n{day} at {s['tour_time']}\n{s['available']} seats currently available\nBook: {link}")
  send_email('TourWatch: a tour opening just appeared!', '\n\n'.join(lines)+'\n\nAvailability can disappear quickly. TourWatch does not reserve tickets.')

 if os.getenv('TOURWATCH_TEST_EMAIL','').lower() in ('1','true','yes'):
  sample=next(iter(details.values()),None)
  body='TourWatch email delivery test succeeded.'
  if sample:
   _,day,s=sample; body+=f"\n\nLive sample: {s['tour_name']} — {day} at {s['tour_time']} — {s['available']} seats."
  send_email('TourWatch TEST alert',body)

 STATE_PATH.write_text(json.dumps({'initialized':True,'updated_at':datetime.now().astimezone().isoformat(),'available':current},indent=2,sort_keys=True)+'\n')
 return 0
if __name__=='__main__': raise SystemExit(main())
