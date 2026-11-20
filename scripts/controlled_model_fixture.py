"""Deterministic local model transport fixture, not an intelligent agent.

The real product Harness calls this loopback-only HTTP server. It emits one
frozen MCP request, then a fixed terminal message. It never interprets task or
Skill instructions and never contacts an external inference service.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
import time

MODEL = 'fixed-tool-v1'
MARKER = 'CONTROLLED_TOOL_V1'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def tool_candidates(tools, parent=None):
    result=[]
    for tool in tools:
        if not isinstance(tool,dict):
            continue
        if tool.get('type')=='namespace':
            result.extend(tool_candidates(tool.get('tools',[]),tool.get('name')))
            continue
        function=tool.get('function',tool)
        name=function.get('name','')
        if isinstance(name,str) and re.fullmatch(r'(?:mcp__[^.]+__)?probe_commit',name):
            result.append({'name':name,'namespace':parent,
                           'schema_sha256':sha(encoded(function.get('parameters',{})))})
    return result


def marked_payloads(value):
    """Extract only our synthetic return object, not system/Skill text."""
    found=[]
    if isinstance(value,dict):
        if value.get('marker')==MARKER:
            return [value]
        for child in value.values():
            found.extend(marked_payloads(child))
    elif isinstance(value,list):
        for child in value:
            found.extend(marked_payloads(child))
    elif isinstance(value,str):
        try:
            decoded=json.loads(value)
        except ValueError:
            decoded=None
        if isinstance(decoded,(dict,list)):
            found.extend(marked_payloads(decoded))
        else:
            for match in re.finditer(r'\{\s*"marker"\s*:',value):
                try:
                    decoded,_=json.JSONDecoder().raw_decode(value[match.start():])
                except ValueError:
                    continue
                if isinstance(decoded,dict) and decoded.get('marker')==MARKER:
                    found.append(decoded)
    return found


def result_items(body):
    return [item for item in body.get('input',body.get('messages',[]))
            if isinstance(item,dict) and
            (item.get('type')=='function_call_output' or item.get('role')=='tool')]


def response_events(item, number):
    response={'id':f'resp_controlled_{number}','object':'response','created_at':int(time.time()),
              'status':'completed','model':MODEL,'output':[item],
              'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}
    initial={**response,'status':'in_progress','output':[],'usage':None}
    events=[{'type':'response.created','response':initial},
            {'type':'response.in_progress','response':initial},
            {'type':'response.output_item.added','output_index':0,
             'item':{**item,'arguments':''} if item['type']=='function_call' else {**item,'content':[]}}]
    if item['type']=='function_call':
        events += [
            {'type':'response.function_call_arguments.delta','item_id':item['id'],'output_index':0,'delta':item['arguments']},
            {'type':'response.function_call_arguments.done','item_id':item['id'],'output_index':0,'arguments':item['arguments']}]
    else:
        part=item['content'][0]
        events += [
            {'type':'response.content_part.added','item_id':item['id'],'output_index':0,'content_index':0,'part':{'type':'output_text','text':'','annotations':[]}},
            {'type':'response.output_text.delta','item_id':item['id'],'output_index':0,'content_index':0,'delta':part['text']},
            {'type':'response.output_text.done','item_id':item['id'],'output_index':0,'content_index':0,'text':part['text']},
            {'type':'response.content_part.done','item_id':item['id'],'output_index':0,'content_index':0,'part':part}]
    events += [{'type':'response.output_item.done','output_index':0,'item':item},
               {'type':'response.completed','response':response}]
    return events


class FixtureState:
    def __init__(self, arguments, journal):
        self.arguments=arguments
        self.journal=Path(journal)
        self.lock=threading.Lock()
        self.requests=0

    def record(self, value):
        with self.journal.open('a',encoding='utf-8',newline='\n') as f:
            f.write(json.dumps({'at':now(),**value},ensure_ascii=False)+'\n')

    def answer(self, path, body, raw):
        with self.lock:
            self.requests+=1
            number=self.requests
            candidates=tool_candidates(body.get('tools',[]))
            returns=result_items(body)
            matched=[item for item in returns if
                     item.get('call_id' if path.endswith('/responses') else 'tool_call_id')=='call_controlled_1']
            payloads=marked_payloads([item.get('output' if path.endswith('/responses') else 'content')
                                     for item in matched])
            # Headers and raw prompt bodies are deliberately not recorded.
            messages=body.get('messages',body.get('input',[]))
            text=json.dumps(messages,ensure_ascii=False)
            self.record({'kind':'model_request','sequence':number,'path':path,
                'request_sha256':sha(raw),'request_bytes':len(raw),'model':body.get('model'),
                'tool_candidates':candidates,'tool_return_items':returns,
                'fixture_return_payloads':payloads,
                'context_bytes':len(text.encode('utf-8')),
                'skill_catalog_header_observed':bool(re.search(r'<available_skills>|### Available skills|## Skills',text)),
                'decision_basis':'sequence and our exact tool identity only; task/Skill instructions ignored'})
            if body.get('model')!=MODEL:
                raise ValueError('Unexpected model identity at local fixture')
            if number==1:
                if returns or len(candidates)!=1:
                    raise ValueError('Need exactly one exposed probe_commit tool before dispatch')
                selected=candidates[0]
                self.record({'kind':'fixed_tool_request','sequence':number,
                             'canonical_tool':'probe_commit','native_tool':selected,
                             'arguments':self.arguments,'arguments_sha256':sha(encoded(self.arguments))})
                return {'type':'function_call','id':'fc_controlled_1','call_id':'call_controlled_1',
                        'name':selected['name'],'arguments':encoded(self.arguments).decode('utf-8'),
                        'status':'completed',**({'namespace':selected['namespace']} if selected['namespace'] else {})}
            if number==2 and len(returns)==1 and len(matched)==1 and len(payloads)==1:
                self.record({'kind':'fixed_terminal','sequence':number,'text':'CONTROLLED_DONE'})
                return {'type':'message','id':'msg_controlled_2','role':'assistant','status':'completed',
                        'content':[{'type':'output_text','text':'CONTROLLED_DONE','annotations':[]}]}
            raise ValueError('Unexpected retry, missing return, or extra model request; retain as calibration/unknown')


class FixtureServer:
    def __init__(self, arguments, journal):
        state=self.state=FixtureState(arguments,journal)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass

            def do_GET(self):
                data=encoded({'object':'list','data':[{'id':MODEL,'object':'model','owned_by':'local-fixture'}]})
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

            def do_POST(self):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if length<=0 or length>16*1024*1024:
                        raise ValueError('Unexpected request size')
                    raw=self.rfile.read(length)
                    body=json.loads(raw)
                    if self.path not in ('/v1/responses','/v1/chat/completions'):
                        raise ValueError('Unknown fixture endpoint')
                    item=state.answer(self.path,body,raw)
                    self.send_response(200);self.send_header('Content-Type','text/event-stream')
                    self.send_header('Cache-Control','no-cache');self.send_header('Connection','close');self.end_headers()
                    if self.path.endswith('/responses'):
                        for event in response_events(item,state.requests):
                            self.wfile.write(b'event: '+event['type'].encode()+b'\ndata: '+encoded(event)+b'\n\n')
                    else:
                        delta={'role':'assistant','content':None}
                        if item['type']=='function_call':
                            delta['tool_calls']=[{'index':0,'id':item['call_id'],'type':'function',
                                'function':{'name':item['name'],'arguments':item['arguments']}}]
                            finish='tool_calls'
                        else:
                            delta['content']='CONTROLLED_DONE';finish='stop'
                        base={'id':'chatcmpl_controlled','object':'chat.completion.chunk',
                              'created':int(time.time()),'model':MODEL}
                        for value in ({**base,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},
                                      {**base,'choices':[{'index':0,'delta':{},'finish_reason':finish}],
                                       'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}):
                            self.wfile.write(b'data: '+encoded(value)+b'\n\n')
                        self.wfile.write(b'data: [DONE]\n\n')
                    self.wfile.flush();self.close_connection=True
                except Exception as exc:
                    state.record({'kind':'fixture_transport_error','error_type':type(exc).__name__,'reason':str(exc)})
                    try:
                        data=encoded({'error':{'message':str(exc),'type':'fixture_protocol_error'}})
                        self.send_response(400);self.send_header('Content-Type','application/json')
                        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
                    except OSError:
                        pass
        self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)

    @property
    def base_url(self):
        return f'http://127.0.0.1:{self.http.server_port}/v1'

    def __enter__(self):
        self.thread.start();return self

    def __exit__(self,*args):
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=5)
