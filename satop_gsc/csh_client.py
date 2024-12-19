import asyncio
from dataclasses import dataclass
import dataclasses
import uuid
import websockets
import json
from datetime import timedelta
from skyfield.api import load, EarthSatellite, wgs84, Time


from csh import csh_wrapper as csh

location =  {
    'latitude':  +56.1717551,
    'longitude': +10.1891487,
    'elevation': 60
}

satellites = {
    'DISCO-1': {
        'tx': True,
        'rx': True,
        'tle': [
            "1 56222U 23054AW  24353.67685951  .00225592  00000+0  13568-2 0  9994",
            "2 56222  97.3318 255.2963 0005670 125.2407 234.9391 15.77072259 94741"
        ]
    }
}

@dataclass
class Observation:
    rise: Time = None
    set: Time = None
    culmination: Time = None
    duration: int = None
    max_angle: float = None

    def add_event(self, t:Time, e):
        match e:
            case 0:
                self.rise = t
            case 1:
                self.culmination = t
            case 2:
                self.set = t
                if self.rise is None or self.culmination is None:
                    return -1
        return e
    
    def evaluate(self, gs, sat):
        assert self.rise is not None
        assert self.culmination is not None
        assert self.set is not None

        self.duration = self.set.utc_datetime() - self.rise.utc_datetime()

        difference = sat-gs
        alt, az, dist = difference.at(self.culmination).altaz()

        self.max_angle = alt.degrees
    
    def flatten(self):
        self.rise = self.rise.utc_iso()
        self.culmination = self.culmination.utc_iso()
        self.set = self.set.utc_iso()
        self.duration = self.duration.seconds
        self.max_angle = float(self.max_angle)


def get_passes(satellite_name: str, min_degrees=30, delta_days=7): 
    sat = satellites.get(satellite_name)
    if not sat:
        return []
    
    gs = wgs84.latlon(location['latitude'], location['longitude'])
    ts = load.timescale()
    t0 = ts.now()
    t1 = ts.now()+timedelta(days=delta_days)

    satellite = EarthSatellite(*sat.get('tle'), satellite_name, ts)

    observations = []
    current_observation = Observation()

    t, events = satellite.find_events(gs, t0, t1)
    for ti, event in zip(t, events):
        added = current_observation.add_event(ti, event)
        if added == 2:
            current_observation.evaluate(gs, satellite)
            current_observation.flatten()
            observations.append(current_observation)
            current_observation = Observation()
        elif added == -1:
            current_observation = Observation()
    
    return list(filter(lambda o: o.max_angle > min_degrees, observations))

def pp_list(l):
    print('[\n  ', end='')
    for i in l:
        print(i, end='\n  ')
    print('\r]')

 
async def main():
    async with websockets.connect('ws://localhost:7890/api/gs/ws') as ws:

        await ws.send(json.dumps({
            'type': 'hello',
            'name': 'CSH Client'
        }))
        print('Connected')

        csh.run('csp init -m "CSH Client"')
        csh.run('ident')
        csh.run('ping 0')

        while True:
            msg = json.loads(await ws.recv())
            print('>' + str(msg))
            req_id = msg.get('request_id')
            data = msg.get('data')
            dtype = data.get('type')

            try:

                match dtype:
                    case 'echo':
                        out = json.dumps({
                            'message_id': str(uuid.uuid4()),
                            'in_response_to': req_id,
                            'data': data
                        })
                        print('<' + out)
                        await ws.send(out)
                    case 'csh':
                        script = data.get('script', [])
                        out, ret = csh.execute_script(script)
                        response = json.dumps({
                            'message_id': str(uuid.uuid4()),
                            'in_response_to': req_id,
                            'data': {
                                'return_code': {
                                    'name': ret.name,
                                    'value': ret.value
                                },
                                'command_output': out.decode()
                            }
                        })

                        print(response)
                        await ws.send(response)
                    case 'station_details':
                        response = json.dumps({
                            'message_id': str(uuid.uuid4()),
                            'in_response_to': req_id,
                            'data': {
                                'location': location,
                                'satellites': list(satellites.keys())
                            }
                        })
                        await ws.send(response)
                    case 'get_satellite_observations':
                        sat_name = data.get('satellite')
                        min_degree = data.get('min_degree', 30)
                        delta_days = data.get('delta_days', 7)
                        response = json.dumps({
                            'message_id': str(uuid.uuid4()),
                            'in_response_to': req_id,
                            'data': {
                                'observations': list(map(lambda o: dataclasses.asdict(o), get_passes(sat_name, min_degree, delta_days)))
                            }
                        })
                        print(response)
                        await ws.send(response)
            except Exception as e:
                print("error", e)
                await ws.send(json.dumps({
                    'message_id': str(uuid.uuid4()),
                    'in_response_to': req_id,
                    'error': 'Server error'
                }))


if __name__ == "__main__":
    asyncio.run(main())