import argparse
import asyncio
import dataclasses
import datetime

import json
from uuid import uuid4
from websockets import Data
from satop_client import SatopClient

from csh.csh_wrapper import CSH
from ground_station_setup import get_available_sattelites, get_gs_location
from observations import get_passes
from scheduler import CSHScheduler
from satop_api import SatopApi

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='localhost')
parser.add_argument('--port', type=int, default=7890)
parser.add_argument('--https', type=bool, default=False)

args = parser.parse_args()

client = SatopClient(args.host, args.port)
api = SatopApi(client.id, args.host, args.port, https=args.https)
csh = CSH(debug=True)
scheduler = CSHScheduler(csh, api)


@client.add_responder('echo')
def echo_responder(data:dict):
    api.log_received_echo(data)
    return data

@client.add_responder('csh')
def csh_responder(data:dict):
    script = data.get('script', [])
    _, artifact_sha1 = api.log_received_commands(script)
    api.log_executed_commands_start(artifact_sha1)
    res = csh.execute_script(script)
    api.log_executed_commands_finish(artifact_sha1, res)
    return res

@client.add_responder('station_details')
def sdr():
    satellites = get_available_sattelites()
    location = get_gs_location()
    print('Getting station details')
    return {
        'location': location,
        'satellites': list(satellites.keys())
    }

@client.add_responder('get_observations')
def observe_responder(satellite, min_degree=30, delta_days=7):
    return {
        'observations': list(map(lambda o: dataclasses.asdict(o), get_passes(satellite, min_degree, delta_days)))
    }

@client.add_responder('schedule_transmission')
def schedule(time, satellite, dataframes: list[Data]):
    dtime = datetime.datetime.fromisoformat(time)
    satellites = get_available_sattelites()
    if not satellite in satellites:
        return {
            'error': {
                'status': 404,
                'detail': 'satellite not found'
            }
        }
    if dtime < datetime.datetime.now(tz=datetime.timezone.utc):
        return {
            'error': {
                'status': 400,
                'detail': 'Cannot schedule event in the past'
            }
        }
    num_frames = len(dataframes)
    if not num_frames == 1:
        return {
            'error': {
                'status': 400,
                'detail': 'Expected 1 frame containing the script to schedule'
            }
        }
    data = json.loads(dataframes[0])
    print(f'Schedule for transmission at {dtime}')
    print(data)
    scheduler.add(start_time=dtime, commands=data, id=uuid4().hex)
    return {}
        


@client.add_responder('test_frames')
def observe_responder(dframes:list[str|bytes]):
    print(f'Recieved {len(dframes)} frames')
    for n,frame in enumerate(dframes):
        print(f' Frame {n}, {type(frame)}, {len(frame)}')
    return {}


async def main():
    await client.connect()
    print('Connected')

    csh.execute('csp init -m "CSH Client"')
    csh.execute('ident')

    await client.run()

    return

if __name__ == "__main__":
    asyncio.run(main())