import argparse
import asyncio
import dataclasses
import datetime

from websockets import Data
from satop_client import SatopClient

from csh import csh_wrapper as csh
from ground_station_setup import get_available_sattelites, get_gs_location
from observations import get_passes

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='localhost')
parser.add_argument('--port', type=int, default=7890)

args = parser.parse_args()

client = SatopClient(args.host, args.port)

@client.add_responder('echo')
def echo_responder(data:dict):
    return data

@client.add_responder('csh')
def csh_responder(data:dict):
    script = data.get('script', [])
    out, ret = csh.execute_script(script)

    return {
        'return_code': {
            'name': ret.name,
            'value': ret.value
        },
        'command_output': out.decode()
    }

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


@client.add_responder('test_frames')
def observe_responder(dframes:list[str|bytes]):
    print(f'Recieved {len(dframes)} frames')
    for n,frame in enumerate(dframes):
        print(f' Frame {n}, {type(frame)}, {len(frame)}')
    return {}

async def main():
    await client.connect()
    print('Connected')

    csh.run('csp init -m "CSH Client"')
    csh.run('ident')

    await client.run()

    return

if __name__ == "__main__":
    asyncio.run(main())