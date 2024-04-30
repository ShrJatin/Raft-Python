from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RequestVoteArgs(_message.Message):
    __slots__ = ("term", "candidateId", "lastLogTerm", "lastLogIndex")
    TERM_FIELD_NUMBER: _ClassVar[int]
    CANDIDATEID_FIELD_NUMBER: _ClassVar[int]
    LASTLOGTERM_FIELD_NUMBER: _ClassVar[int]
    LASTLOGINDEX_FIELD_NUMBER: _ClassVar[int]
    term: int
    candidateId: int
    lastLogTerm: int
    lastLogIndex: int
    def __init__(self, term: _Optional[int] = ..., candidateId: _Optional[int] = ..., lastLogTerm: _Optional[int] = ..., lastLogIndex: _Optional[int] = ...) -> None: ...

class RequestVoteReply(_message.Message):
    __slots__ = ("voteGranted", "term", "remainingLease")
    VOTEGRANTED_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    REMAININGLEASE_FIELD_NUMBER: _ClassVar[int]
    voteGranted: bool
    term: int
    remainingLease: float
    def __init__(self, voteGranted: bool = ..., term: _Optional[int] = ..., remainingLease: _Optional[float] = ...) -> None: ...

class AppendEntriesArgs(_message.Message):
    __slots__ = ("term", "leaderId", "prevLogTerm", "prevLogIndex", "leaseInterval", "entries", "leaderCommit")
    TERM_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    PREVLOGTERM_FIELD_NUMBER: _ClassVar[int]
    PREVLOGINDEX_FIELD_NUMBER: _ClassVar[int]
    LEASEINTERVAL_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    LEADERCOMMIT_FIELD_NUMBER: _ClassVar[int]
    term: int
    leaderId: int
    prevLogTerm: int
    prevLogIndex: int
    leaseInterval: int
    entries: _containers.RepeatedCompositeFieldContainer[LogEntry]
    leaderCommit: int
    def __init__(self, term: _Optional[int] = ..., leaderId: _Optional[int] = ..., prevLogTerm: _Optional[int] = ..., prevLogIndex: _Optional[int] = ..., leaseInterval: _Optional[int] = ..., entries: _Optional[_Iterable[_Union[LogEntry, _Mapping]]] = ..., leaderCommit: _Optional[int] = ...) -> None: ...

class AppendEntriesReply(_message.Message):
    __slots__ = ("success", "term")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    success: bool
    term: int
    def __init__(self, success: bool = ..., term: _Optional[int] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ("term", "data")
    TERM_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    term: int
    data: str
    def __init__(self, term: _Optional[int] = ..., data: _Optional[str] = ...) -> None: ...

class ServeClientArgs(_message.Message):
    __slots__ = ("Request",)
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    Request: str
    def __init__(self, Request: _Optional[str] = ...) -> None: ...

class ServeClientReply(_message.Message):
    __slots__ = ("Data", "LeaderID", "Success")
    DATA_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    Data: str
    LeaderID: int
    Success: bool
    def __init__(self, Data: _Optional[str] = ..., LeaderID: _Optional[int] = ..., Success: bool = ...) -> None: ...
