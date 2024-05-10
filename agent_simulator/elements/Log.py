import time

class Log:
    def __init__(self, sim_config:dict):
        self.sim_config = sim_config
        self.simulation_timestamp = time.time()
        self.log = list()
    
    def log_action(self, time:float, action:str, item_type:str, item_id:str):
        self.log.append({
            'time': time,
            'action': action,
            'item_type': item_type,
            'item_id': item_id
        })
        return self

    @property
    def length(self) -> int:
        return len(self.event_log)

    def __repr__(self):
        return f"Log(length={self.length})"