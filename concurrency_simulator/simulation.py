import numpy as np
import random

from .contact import Contact
from .event import Event

class Simulation:
    def __init__(
        self,
        interval:int,
        max_concurrency:int,
        contact_types:dict=None,
        concurrency_floor:float = 0
    ):
        #Attributes
        self.interval = interval
        self.max_concurrency = max_concurrency
        self.contact_types = dict()
        self.concurrency_floor = concurrency_floor
        #Simulation Carries
        self.chain_position = 0
        self.current = 0
        self.waiting = list() # of Contacts
        self.events = list() # of Events
        #Outputs
        self.handled = list() # of Contacts
        self.missed = list() # of Contacts
        #Accumulators
        self.lines_acc = list()
        self.handling_time_acc = 0

    # Reset
    def reset(self):
        self.waiting = []
        self.events = []
        self.current = 0
        self.chain_position = 0
        self.lines_acc = list()
        self.volumes_acc = 0
        self.handled = []
        self.missed = []
        
    def get_handled(self) -> list:
        return [r.to_dict() for r in self.handled]
    
    def get_missed(self) -> list:
        return [r.to_dict() for r in self.missed]
    
    def get_solved(self) -> list:
        return [*self.get_handled(),*self.get_missed()] 
        
    def get_waiting(self) -> list:
        return [r.to_dict() for r in self.waiting]
    
    def get_agent_time(self) -> float:
        return np.sum(self.lines_acc) * (self.interval)/ self.max_concurrency
    
    def get_handling_times(self) -> float:
        return self.handling_time_acc
        
    # Add and Remove Contact Types
    def add_contact_type(
        self, 
        name:str, 
        aht:tuple, 
        average_patience:float = None, 
        auto_solve_time:float = None
    ) -> None:
        """
            Usage: Create a contact type.
            Arguments:
            -name: must be unique within contact_types, will overwrite otherwise.
            -aht: must be a tuple of 2 numeric values (a, b) from which total AHT
            will be calculated in the following way: [ a + b x concurrency ]
            -average_patience: Optional, if ommitted, infinite patience is assumed.
            -auto-solve-time: Optional, if ommitted, no there will be no auto-solves during simulation.
        """
        
        if not (len(aht) == 2 and all(isinstance(x, (int, float)) and x >= 0 for x in aht)):
            print("ValErr: 'aht' must be a tuple of 2 positive numeric values.")
            
        self.contact_types[name] =  {
            'aht': aht,
            'average_patience': average_patience,
            'auto_solve_time': auto_solve_time
        }       
        
    def remove_contact_type(self, name:str) -> None:
        removed = self.contact_types.pop(name, None)
        if removed:
            print(f'Removed {name} contact type successfully.')
        else:
            print(f'Nothing to remove.')
        
    def list_contact_types(self) -> list:
        return list(self.contact_types.keys())
    
    #SIMULATION HELPER METHODS
    def _generate_events_list(self, volumes:dict) -> list:
        new_events = []
        for ct_name, ct in self.contact_types.items():
            for _ in range(volumes[ct_name]):
                new_contact = Contact(
                    aht = ct['aht'], 
                    interval = self.interval,
                    contact_type = ct_name,
                    shift_index = self.chain_position,
                    average_patience = ct['average_patience'],
                    auto_solve_time = ct['auto_solve_time']
                )
                new_events.append(Event(item=new_contact, time=new_contact.arrival_time, event_type='arrival'))

        return new_events

    def _handle_next_waiting(self, handling_start:float ,lines:int):
        waiting_contact:Contact = self.waiting.pop(0)
        contact_type = self.contact_types[waiting_contact.contact_type]
        concurrency = (self.current + 1) / lines * self.max_concurrency
        waiting_contact.materialise_handling(handling_start, concurrency, self.concurrency_floor)
        if waiting_contact.status == 'handled':
            self.current += 1
            waiting_contact.set_lines(available=lines, occupied=self.current)
            self.handled.append(waiting_contact)
            self.handling_time_acc += waiting_contact.handling_time
            self.events.append(Event(item=waiting_contact, time=waiting_contact.end_time, event_type='solve'))
        else:
            self.missed.append(waiting_contact)
           
    def _handle_arriving_contact(self, new_contact:Contact, handling_start:float, lines:int):
        if self.current < lines:
            self.current += 1
            concurrency = self.current / lines * self.max_concurrency
            new_contact.materialise_handling(handling_start, concurrency, self.concurrency_floor)
            new_contact.set_lines(available=lines, occupied=self.current)
            self.handled.append(new_contact)
            self.handling_time_acc += new_contact.handling_time
            self.events.append(Event(item=new_contact, time=new_contact.end_time, event_type='solve'))
        else:
            self.waiting.append(new_contact)
    
    #MAIN SIMULATION METHOD
    def simulate(self, volumes:dict, lines:int):
        # Verify that volumes match contact types
        if set(volumes.keys()) != set(self.contact_types.keys()):
            print(f"ValErr: 'volumes' don't match 'contact_types'. Make sure 'volumes' has \
                      integer values for the following keys: {self.contact_types.keys()}")
        
        # Assign All Waiting Contacts to Newly Available Lines (if any are available)
        while lines > self.current and len(self.waiting):
                self._handle_next_waiting(self.chain_position * self.interval ,lines)
        
        # Generate All Contacts & Events
        new_events = self._generate_events_list(volumes)  
        self.events = [*self.events, *new_events]

        #Iterate Through All Events
        while len(self.events) > 0:
            self.events = sorted(self.events, key = lambda event: event.time)
            next_event:Event = self.events.pop(0)
            #Overflows Iterval
            if next_event.time >= (1 + self.chain_position) * self.interval:
                self.events.append(next_event)
                break
            #Event Is Arrival
            elif(next_event.istype('arrival')):
                self._handle_arriving_contact(next_event.item, handling_start=next_event.time, lines=lines)
            #Event Is Solve
            else:
                self.current -= 1
                while len(self.waiting) > 0 and lines > self.current:
                    self._handle_next_waiting(next_event.time,lines)
    
        self.chain_position += 1
        self.lines_acc.append(lines)
        
    #SIMULATION ITERATORS
    def coverage_test(self, volumes:dict, lines:int, intervals:int=10) -> None:
        """
            Usage: This test will perform the simulation for a set amount of consecutive intervals, 
            with a fixed number of lines and volumes. This is useful to understand the equilibrium 
            state of this specific level of coverage for a certain amount of traffic.
            
            Arguments:
            -volumes: Volumes dictionary. Direct input for the 'simulate' method.
            -lines: Lines available to answer contacts. Direct input for the 'simulate' methiod.
            -intervals: Number of consecutive intervals (iterations) to simulate.
        """
        
        self.reset()
        for _ in range(intervals):
            self.simulate(volumes, lines)
            
    def transition_test(self, volumes_start:dict, volumes_end:dict, lines_start:int, lines_end:int, intervals_start:int=10, intervals_end:int=1) -> None:
        """
            Usage: This test will perform the a 2-staged simulation. First will perform the sumulation with 'volumes_start' 
            and 'lines_start' for 'intervals_start' amount of intervals. Consecutively will simulate with 'volumes_end' and 
            'lines_end' for 'intervals_end' amount of intervals.
            
            Arguments:
            -volumes_start: Volumes dictionary for 'start' stage. Direct input for the 'simulate' method.
            -volumes_end: Volumes dictionary for 'end' stage. Direct input for the 'simulate' method.
            -lines_start: Lines available to answer contacts for 'start' stage. Direct input for the 'simulate' methiod.
            -lines_end: Lines available to answer contacts for 'end' stage. Direct input for the 'simulate' methiod.
            -intervals_start: Number of consecutive intervals (iterations) to simulate on 'start' stage.
            -intervals_end: Number of consecutive intervals (iterations) to simulate on 'end' stage.
        """
        
        self.reset()
        for _ in range(intervals_start):
            self.simulate(volumes_start, lines_start)
        for _ in range(intervals_end):
            self.simulate(volumes_end, lines_end)
            
    #COVERAGE TRANSFORMERS
    @staticmethod
    def scale_transform(coverage:np.ndarray, scale_factor:float, unit:float=1) -> np.ndarray:
        """
            Usage: Used to scale a coverage array by 'scale_factor'.
        """
        return np.round(coverage * scale_factor / unit) * unit
    
    @staticmethod
    def shrinkage_transform(coverage:np.ndarray, shrinkage:np.ndarray) -> np.ndarray:
        """
            Usage: Used to apply a 'shrinkage' percetage value for every element of 'coverage'.
            Arrays must have same shape. A value of 0.05 on 'shrinkage' array will produce an output,
            on the same position, equal to 95% of the value of 'coverage'. 
            A negative value will output 105%.
        """
        if coverage.shape != shrinkage_array.shape:
            print("ValErr: Arguments 'coverage' and 'shrinkage' must have same shape.")
            return
        else:
            return coverage * (1-shrinkage)
    
    @staticmethod
    def t_smooth_transform(coverage:np.ndarray, smooth_factor:int=2, unit:float=1) -> np.ndarray:
        """
            Usage: Will transform 'coverage' with a transition smoothing algorythm. Smaller 'smooth_factor's
            will lead to bigger effects, with the lower limit being 1. This edge case will simply subtract the 
            differences array.
            
            Arguments:
            -smooth_factor: Main parameter for the smoothing algorythm. Positive Integer.
            -unit: Minimum unit size for the differences applied. Will be used for rounding purposes
        """
        if smooth_factor <= 0:
            print("ValErr: Argument 'smooth_factor' must be a positive integer.")
            return
        else:
            
            diffs = np.array([0, * np.diff(coverage)])
            return np.round((coverage - diffs / smooth_factor)/unit) * unit
        
    @staticmethod
    def f_log_transform(coverage:np.ndarray, power:float=2.0, threshold:int=5, unit:float=1) -> np.ndarray:
        """
            Usage: Will transform 'coverage' by applying a pseudo-filter. This transform is useful to treat coverages 
            generated by Erlang models. The need for this transform comes from the somewhat conservative values at high
            traffic intervals. This transform may also increase the low traffic coverage as they pose higher risk of
            underperformance.
            
            Values bellow 'threshold' may only be increased, and the ones over the threshold may only be decreased.
            The effect will be proportionally regulated by 'power' and finally rounded to the 'unit'.
        """
        
        return coverage - np.round(power * np.log(coverage / threshold) / unit) * unit