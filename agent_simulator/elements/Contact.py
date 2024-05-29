import math
import uuid
import random
import numpy as np

class Contact:
    def __init__(
        self,
        arrival:int = 0,
        contact_type:str='basic',
        ht_distro:str='gamma-2',
        average_patience:float=None,
        auto_solve_time:float=None
    ):
        self.id = str(uuid.uuid4())
        self.arrival = arrival
        self.concurrency_at_arrival = None
        self.concurrency_history = list()
        self.contact_type = contact_type
        self.ht_distro = ht_distro
        self.status = "created"
        self.waiting_time = 0
        self.handling_time = None
        self.patience = round(np.random.exponential(scale=average_patience)) if average_patience else math.inf
        self.auto_solve_time = auto_solve_time if auto_solve_time else math.inf
    
    def materialise_handling(self, handling_start:float, aht:float, concurrency:int=1.0)->"Contact":
        waiting_time =  handling_start - self.arrival if handling_start else 0
        
        if(waiting_time > self.patience):
            self.status = 'abandoned'
            self.waiting_time = self.patience
        elif(waiting_time > self.auto_solve_time):
            self.status = 'auto-solved'
            self.waiting_time = self.auto_solve_time
        else:
            self.status = 'handled'
            if self.ht_distro == 'gamma-2':
                self.handling_time = max(min(np.random.gamma(2, aht/2), aht * 15), 0.1)
            if self.ht_distro == 'exponential':
                self.handling_time = max(min(np.random.exponential(aht), aht * 15), 0.1)
            self.concurrency_at_arrival = concurrency
            self.concurrency_history.append({"concurrency": concurrency, "time": handling_start})
            self.waiting_time = waiting_time
        return self
    
    def update_handling(self, present:float, factor:float, new_concurrency:int)->"Contact":
        handling_end = self.arrival + self.waiting_time + self.handling_time
    
        if round(present) > round(handling_end):
            print(f"Contact | Contact handling ends in the past (before {present}) -> ", self)
        else:
            remaining_time = handling_end - present
            new_remaining_time = remaining_time * factor 
            self.concurrency_history.append({"concurrency": new_concurrency, "time": present})
            self.handling_time += (new_remaining_time - remaining_time)
        return self

    def get_current_concurrency(self)->"Contact":
        return self.concurrency_history[-1]

    def check_missed(self, present) -> bool:
        waiting_time =  present - self.arrival
        return (waiting_time > self.patience) | (waiting_time > self.auto_solve_time)
        
        
    
    #PROPERTIES   
    @property
    def arrival_at(self) -> int:
        return self.arrival
    
    @property
    def start_at(self) -> int:
        return self.arrival + self.waiting_time
    
    @property
    def end_at(self) -> int:
        return self.arrival + self.waiting_time + self.handling_time if self.handling_time else None
        
    @property
    def total_duration(self) -> int:
        return self.waiting_time + self.handling_time if self.handling_time else None
        
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'arrival': self.arrival,
            'waiting_time': self.waiting_time,
            'handling_time': self.handling_time,
            'patience': self.patience,
            'status': self.status,
            'contact_type': self.contact_type,
            'concurrency_at_arrival': self.concurrency_at_arrival,
            'concurrency_history': self.concurrency_history
        }

    def __repr__(self):
        return f"Contact(contact_type={self.contact_type},arrival={self.arrival},waiting_time={self.waiting_time},handling_time={self.handling_time})"
