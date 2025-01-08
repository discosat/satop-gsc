import datetime
import dataclasses
import threading
import time
from csh.csh_wrapper import CSH
from satop_api import SatopApi

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

@dataclasses.dataclass
class ScheduledElement:
    time: datetime.datetime 
    csh: list[str]
    thread: threading.Timer

class CSHScheduler:
    api: SatopApi
    csh_busy:bool = False
    csh: CSH
    scheduled:dict[str, ScheduledElement]


    def __init__(self, csh:CSH, api:SatopApi):
        self.scheduled = dict()
        self.csh = csh
        self.api = api
        self.load()
        pass

    def load(self):
        """Load currently saved schedules from non-volitile storage
        """
        pass
    
    def add(self, start_time:datetime.datetime, commands: list[str], id: str):
        """Add a new CSH script to schedule

        Args:
            start_time (datetime.datetime): _description_
            commands (list[str]): _description_
            id (str): script identifier
        """
        dt = start_time-utcnow()
        delta_time = (dt.seconds * (10**6) + dt.microseconds)/(10**6)
        print(f'Adding {id} to schedule to run at {start_time} (in {delta_time} s)')

        _, artifact_sha1 = self.api.log_received_commands(commands, start_time.timestamp())
        t = threading.Timer(delta_time, self.execute_commands, args=(commands,id,artifact_sha1))
        ev = ScheduledElement(
            time = start_time,
            csh = commands,
            thread=t
        )

        self.scheduled[id] = ev

        t.start()

    def remove(self, id:str):
        """Remove an element from the schedule

        Args:
            id (str): _description_
        """
        s = self.scheduled.get(id)
        if s:
            s.thread.cancel()
            self.scheduled.pop(id)

    def execute_commands(self, commands:list[str], id:str, artifact_hash:str):
        expected_start = self.scheduled.get(id).time
        t1 = utcnow()
        dcall = t1-expected_start

        print(f'executing {id}')
        while self.csh_busy:
            time.sleep(1)

        results = []

        self.csh_busy = True
        print(f'{id}')
        t2 = utcnow()
        dstart = t2-expected_start
        self.api.log_executed_commands_start(artifact_hash, dstart)
        for cmd in commands:
            out, ret = self.csh.execute(cmd)
            results.append({
                'in': cmd,
                'out': out.decode(),
                'return_code': {
                    'name': ret.name,
                    'value': ret.value
                },
            })
        self.csh_busy = False
        t3 = utcnow()
        dexec = t3-t2

        print(f'{id} | Called {dcall} after scheduled | Started {dstart} after scheduled | Took {dexec}')
        self.api.log_executed_commands_finish(artifact_hash, results, dexec)

        self.scheduled.pop(id)

    def stop(self):
        for s,se in self.scheduled.items():
            self.remove(s)
            se.thread.join()
