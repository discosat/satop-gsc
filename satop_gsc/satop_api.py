from io import StringIO
import requests
import json
import datetime
from enum import Enum
from typing import IO, Union
from uuid import uuid4, UUID
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    user = 'user'
    system = 'system'

class Entity(BaseModel):
    type: EntityType
    id: str

class Predicate(BaseModel):
    descriptor: str

class Artifact(BaseModel):
    sha1: str

class Action(BaseModel):
    id: str = Field(default_factory=(lambda:str(uuid4())))
    descriptor: str

Value = Union[str, int, float]
Subject = Union[Entity, Artifact, Action]
Object = Union[Entity, Artifact, Action, Value]

class Triple(BaseModel):
    subject: Subject
    predicate: Predicate
    object: Object

class EventRelationshipBase(BaseModel):
    predicate: Predicate

class EventSubjectRelationship(EventRelationshipBase):
    subject: Subject

class EventObjectRelationship(EventRelationshipBase):
    object: Object

class EventBase(BaseModel):
    descriptor: str
    relationships: list[Union[EventSubjectRelationship, EventObjectRelationship, Triple]]

class Event(EventBase):
    id: str
    timestamp: int

class ArtifactUploadResponse(BaseModel):
    name: str
    size: int
    sha1: str

class SatopApi:
    base_url: str
    auth_token: str = None

    def __init__(self, gs_id:UUID, host:str, port:str=None, base_path:str='/api', https:bool=True):
        self.base_url = f"{'https' if https else 'http'}://{host}{':'+port if port is not None else ''}{base_path}"
        self.entity = Entity(type=EntityType.system, id=str(gs_id))
        self._executed_at_relation = EventObjectRelationship(
                predicate=Predicate(descriptor='executedAt'), 
                object=self.entity
            )

    def _authenticate(self, api_key):
        raise NotImplemented
    
    def _get_headers(self):
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
    
    def _log_new_artifact_raw(self, data:IO[bytes], filename:str|None=None, mime_type='application/octet-stream'):
        if filename is None:
            filename = 'gs_artifact_'+datetime.datetime.now(datetime.timezone.utc).isoformat()
        files = {'file':( filename, data, mime_type )}
        print(f"uploading artifacts: {files}")
        response = requests.post(self.base_url + '/log/artifacts', headers=self._get_headers(), files=files)

        if response.status_code == 200:
            print('Artifact already exists')
            return response.json().get('detail').split(' ')[-1]

        elif response.status_code != 201: 
            print(response.status_code)
            print(response.reason)
            print(response.content)
            raise RuntimeError
        
        print(response.content)
        
        result = ArtifactUploadResponse.model_validate_json(response.content)
        return result.sha1
    
    def _log_new_artifact_str(self, data:str, filename:str|None=None):
        b_data = StringIO(data)
        return self._log_new_artifact_raw(b_data, filename, mime_type='text/plain')
    
    def _log_new_artifact_json(self, data:dict|list, filename:str|None=None):
        b_data = StringIO()
        json.dump(data, b_data)
        b_data.seek(0)
        return self._log_new_artifact_raw(b_data, filename, mime_type='application/json')

    def _log_event(self, event:EventBase):
        response = requests.post(self.base_url+'/log/events', headers=self._get_headers(), json=event.model_dump_json())

        if response.status_code != 200:
            print(response.status_code)
            print(response.reason)
            print(response.content)
            raise RuntimeError
        
        return Event.model_validate_json(response.content)


    def log_received_echo(self, content:str):
        sha1 = self._log_new_artifact_str(content)
        event = EventBase(descriptor='gsEchoEvent',relationships=[
            self._executed_at_relation,
            EventObjectRelationship(predicate=Predicate(descriptor='echoing'), object=Artifact(sha1=sha1))
        ])
        self._log_event(event)

    def log_received_commands(self, script:list[str], scheduled_at:int=None):
        sha1 = self._log_new_artifact_str('\n'.join(script))
        event = EventBase(descriptor='gsReceiveCSH',relationships=[
            self._executed_at_relation,
            EventObjectRelationship(predicate=Predicate(descriptor='content'), object=Artifact(sha1=sha1))
        ])
        if scheduled_at:
            event.relationships.append(EventObjectRelationship(
                predicate=Predicate(descriptor='scheduledExecutionAt'),
                object=scheduled_at
            ))
        return self._log_event(event), sha1

    def log_executed_commands_start(self, script_sha1:str, timing_deltastart:datetime.timedelta):
        event = Event(descriptor='startedCommandExecution',relationships=[
            self._executed_at_relation,
            EventObjectRelationship(predicate=Predicate(descriptor='content'), object=Artifact(sha1=script_sha1))
        ])
        if timing_deltastart:
            event.relationships.append(EventObjectRelationship(predicate=Predicate(descriptor='executionScheduleDelay'), 
                                                               object=str(timing_deltastart)))
        return self._log_event(event)

    def log_executed_commands_finish(self, script_sha1:str, result:list, timing_runtime:datetime.timedelta):
        result_sha1 = self._log_new_artifact_json(result)
        event = Event(descriptor='finishedCommandExecution',relationships=[
            self._executed_at_relation,
            EventObjectRelationship(predicate=Predicate(descriptor='content'), object=Artifact(sha1=script_sha1)),
            EventObjectRelationship(predicate=Predicate(descriptor='result'), object=Artifact(sha1=result_sha1))
        ])
        if timing_runtime:
            event.relationships.append(EventObjectRelationship(predicate=Predicate(descriptor='executionRuntime'), 
                                                               object=str(timing_runtime)))
        return self._log_event(event)
