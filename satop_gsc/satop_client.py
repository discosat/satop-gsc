import asyncio
import json
import traceback
import typing
import websockets
from inspect import signature
from typing import get_type_hints, get_args, get_origin
from uuid import uuid4, UUID
from websockets.asyncio.client import ClientConnection
from websockets.typing import Data
from pathlib import Path

def split_origin_args(typ):
    origin = typing.get_origin(typ)
    args = typing.get_args(typ)

    if origin is None:
        origin = typ
        args = None

    return origin, args

class SatopClient:
    responders: dict[str, callable] = dict()
    ws: ClientConnection
    id: UUID | None = None

    def __init__(self, host, port=80, tls=False, api_path='/api/gs'):
        ws_proto, http_proto = ('wss', 'https') if tls else ('ws', 'http')

        base_path = f'{host}:{port}{api_path}'
        self.ws_url = f'{ws_proto}://{base_path}/ws'
        self.gsapi_url = f'{http_proto}://{base_path}'

        self.id_file = Path(__file__).parent.resolve() / '.id'
        if self.id_file.exists():
            with open(self.id_file) as f:
                self.id = UUID(f.read())
        
        @self.add_responder('/methods')
        def get_respond_methods():
            return list(self.responders.keys())


    async def connect(self, timeout = 10):
        async with asyncio.timeout(timeout):
            self.ws = await websockets.connect(self.ws_url)

            hello = {
                'type': 'hello',
                'name': 'CSH Client'
            }
            if self.id:
                hello['id'] = str(self.id)

            await self.ws.send(json.dumps(hello))

            connect_message = json.loads(await self.ws.recv())
            assert connect_message['message'] == 'OK'

            if self.id:
                assert UUID(connect_message['id']) == self.id
            else:
                self.id = UUID(connect_message['id'])
                with open(self.id_file, 'w+') as f:
                    f.write(str(self.id))
    
    async def disconnect(self):
        await self.ws.close(1001)

    def add_responder(self, message_type):
        def decorator(func):
            self.responders[message_type] = func
        return decorator
    
    def error_message(self, in_response_to, code=500, details='Server error'):
        return {
            'message_id': str(uuid4()),
            'in_response_to': in_response_to,
            'error': {
                'status': code,
                'detail': details
            }
        }
    
    async def run(self):
        try:
            while True:
                raw_msg = await self.ws.recv()
                msg = json.loads(raw_msg)
                print(f'ws > {msg}')

                req_id = msg.get('request_id')
                data = msg.get('data', dict())
                dtype = msg.get('type', data.get('type'))
                print(f'Got request with type {dtype}')
                extra_frames = msg.get('frames', 0)
                data_frames = []
                if extra_frames > 0:
                    print(f'Will try to get additional {extra_frames} frames')
                for i in range(extra_frames):
                    data_frames.append(await self.ws.recv())
                    print(f'\r{i+1}/{extra_frames}', end='')
                print()

                if req_id is None or dtype is None:
                    response = self.error_message('')
                    response.pop('in_response_to')
                else:
                    func = self.responders.get(dtype)
                    if not func:
                        response = self.error_message(req_id, 404, 'Method not found')
                    else:
                        try:
                            type_hints = { arg: annotation.annotation for arg,annotation in signature(func).parameters.items() }
                            if 'return' in type_hints:
                                type_hints.pop('return')
                            args = {}
                            for arg, hint in type_hints.items():
                                if arg in data:
                                    args[arg] = data[arg]
                                    print(f'{arg} is named')
                                    continue
                                arg_type, arg_type_args = split_origin_args(hint)
                                if arg_type == list and arg_type_args == (Data,):
                                    args[arg] = data_frames
                                    print(f'{arg} is data_frames')
                                elif arg_type == Data:
                                    args[arg] = raw_msg
                                    print(f'{arg} is raw')
                                elif arg_type == dict:
                                    args[arg] = data
                                    print(f'{arg} is data')
                                else:
                                    print(f'{arg} is none: {split_origin_args(hint)}')

                            response_data = func(**args)

                            response = {
                                'message_id': str(uuid4()),
                                'in_response_to': req_id,
                                'data': response_data
                            }
                        except Exception as e:
                            response = self.error_message(req_id, details=f'{e}, {e.__traceback__.tb_frame}|{e.__traceback__.tb_lasti}|{e.__traceback__.tb_lineno}')
                            traceback.print_exception(e)
                print(f'ws < {response}')
                await self.ws.send(json.dumps(response))
        finally: 
            await self.disconnect()