import math
import uuid
import random
import numpy as np

class Contact:
    def __init__(
        self,
        aht:tuple,
        interval: int,
        contact_type:str='basic',
        shift_index:int=0,
        average_patience:float=None,
        auto_solve_time:float=None
    ):
        self.id = str(uuid.uuid4())
        self.arrival = round((random.uniform(0, 1) + shift_index) * interval, 2)
        self.contact_type = contact_type
        self.aht = aht
        self.status = "created"
        self.waiting_time = 0
        self.concurrency = None
        self.handling_time = None
        self.available_lines = None
        self.occupied_lines = None
        self.patience = round(np.random.exponential(scale=average_patience) + (60 / interval),2) if average_patience else math.inf
        self.auto_solve_time = auto_solve_time if auto_solve_time else math.inf

    def set_lines(self, available:int, occupied:int):
        self.available_lines = available
        self.occupied_lines = occupied
        return self
    
    def materialise_handling(self, handling_start:float, concurrency:float=1.0, concurrency_floor:float=0.0):
        waiting_time =  handling_start - self.arrival if handling_start else 0
        
        if(waiting_time > self.patience):
            self.status = 'abandoned'
            self.waiting_time = self.patience
        elif(waiting_time > self.auto_solve_time):
            self.status = 'auto-solved'
            self.waiting_time = self.auto_solve_time
        else:
            aht = self.aht[0] + self.aht[1] * max(concurrency, concurrency_floor)
            self.status = 'handled'
            self.handling_time = max(min(round(np.random.exponential(scale=aht)), aht * 15), 0.1)
            self.concurrency = concurrency
            self.waiting_time = waiting_time
        return self

    #PROPERTIES   
    @property
    def arrival_time(self) -> int:
        return self.arrival
    @property
    def end_time(self) -> int:
        return self.arrival + self.waiting_time + self.handling_time if self.handling_time else None
        
    @property
    def total_time(self) -> int:
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
            'concurrency': self.concurrency,
            'available_lines':  self.available_lines,
            'occupied_lines': self.occupied_lines
        }