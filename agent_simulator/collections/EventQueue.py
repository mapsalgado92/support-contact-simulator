from ..elements.Event import Event

class EventQueue:
    def __init__(self, fifo=True):
        self.events = list()
        self.fifo = fifo

    def add_event(self, event:Event)->"EventQueue":
        self.events.append(event)
        return self

    def add_event_start(self, event:Event)->"EventQueue":
        self.events.insert(0, event)
        return self

    def get_next_event(self) -> Event:
        if self.next:
            next = self.next
            self.events.remove(next)
            return next
        else:
            print("EventQueue | Can't get next element.")
            return None

    def get_cond_next_event(self, cond) -> Event:
        if self.fifo == False:
            print("EventQueue | Conditional Next only available for FIFO queues.")
            return None
        filtered = list(filter(cond, self.events))
        if len(filtered) > 0:
            next = filtered[0]
            self.events.remove(next)
            return next
        else:
            print("EventQueue | Can't get next conditional element.")
            return None

    def sort(self) -> None:
        self.events = sorted(self.events, key=lambda e: e.time)
        return None

    @property
    def length(self) -> int:
        return len(self.events)
    @property
    def next(self) -> Event:
        if self.length > 0:
            return self.events[0] if self.fifo else min(self.events, key=lambda e:e.time)
        else:
            return None

    def __repr__(self):
        return f"EventQueue(length={self.length},fifo={self.fifo})"


        
        