from typing import Callable

class Event:
    def __init__(
        self,
        item: object,
        event_type: str,
        time:float = None,
        time_callback:Callable = None
    ) -> None:
        if time is not None and time_callback is not None:
            raise ValueError("Either 'time' or 'time_callback' should be provided, not both.")
        self.item = item
        self.event_type = event_type
        self._time_callback = time_callback
        self._time = time

    def istype(self, type_str:str)->bool:
        return type_str == self.event_type

    def set_time(self, time:float)->'Event':
        if self._time_callback is not None:
            print("Event | Event has time callback, can't be hardcoded.")
        else:
            self._time = time
        return self

    @property
    def time(self)->float:
        if self._time_callback is not None:
            return self._time_callback(self.item)
        else:
            return self._time

    def __repr__(self):
        return f"Event(event_type={self.event_type},time={self.time})"

    