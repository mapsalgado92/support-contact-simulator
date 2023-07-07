class Event:
    def __init__(
        self,
        item:object,
        event_type:str,
        time:float
    ) -> None:
        self.item = item
        self.event_type = event_type
        self.time = time

    def istype(self, type_str:str) -> bool:
        return type_str == self.event_type
    