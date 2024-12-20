import asyncio
import json
import typing
import websockets
from inspect import signature
from uuid import uuid4
from websockets.asyncio.client import ClientConnection

class SatopClient:
    responders: dict[str, callable] = dict()
    ws: ClientConnection

    def __init__(self, host, port=80, tls=False, api_path='/api/gs'):
        ws_proto, http_proto = ('wss', 'https') if tls else ('ws', 'http')

        base_path = f'{host}:{port}{api_path}'
        self.ws_url = f'{ws_proto}://{base_path}/ws'
        self.gsapi_url = f'{http_proto}://{base_path}'
    
    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)

        await self.ws.send(json.dumps({
            'type': 'hello',
            'name': 'CSH Client'
        }))
    
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
                'code': code,
                'details': details
            }
        }
    
    async def run(self):
        try:
            while True:
                msg = json.loads(await self.ws.recv())
                print(f'ws > {msg}')

                req_id = msg.get('request_id')
                data = msg.get('data', dict())
                dtype = data.get('type')

                if req_id is None or dtype is None:
                    response = self.error_message('')
                    response.pop('in_response_to')
                else:
                    func = self.responders.get(dtype)
                    if not func:
                        response = self.error_message(req_id, 404, 'Method not found')
                    else:
                        try:
                            func_parameters = signature(func).parameters
                            match len(func_parameters):
                                case 0:
                                    response_data = func()
                                case 1:
                                    response_data = func(data)
                                case _:
                                    response_data = func(**data)
                            response = {
                                'message_id': str(uuid4()),
                                'in_response_to': req_id,
                                'data': response_data
                            }
                        except:
                            response = self.error_message(req_id)
                print(f'ws < {response}')
                await self.ws.send(json.dumps(response))
        finally: 
            await self.disconnect()