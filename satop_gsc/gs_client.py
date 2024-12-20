import asyncio
import dataclasses
from satop_client import SatopClient

from csh import csh_wrapper as csh
from ground_station_setup import get_available_sattelites, get_gs_location
from observations import get_passes

client = SatopClient('localhost', 7890)

@client.add_responder('echo')
def echo_responder(data):
    return data

@client.add_responder('csh')
def csh_responder(data):
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
def observe_responder(satellite, *, min_degree=30, delta_days=7, **_):

    return {
        'observations': list(map(lambda o: dataclasses.asdict(o), get_passes(satellite, min_degree, delta_days)))
    }
 
async def main():
    await client.connect()
    print('Connected')

    csh.run('csp init -m "CSH Client"')
    csh.run('ident')
    csh.run('ping 0')

    await client.run()

    return

if __name__ == "__main__":
    asyncio.run(main())