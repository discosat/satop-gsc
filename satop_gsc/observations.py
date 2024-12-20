import dataclasses
from datetime import timedelta
from skyfield.api import load, EarthSatellite, wgs84, Time
from ground_station_setup import get_available_sattelites, get_gs_location


@dataclasses.dataclass
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
    satellites = get_available_sattelites()
    location = get_gs_location()

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