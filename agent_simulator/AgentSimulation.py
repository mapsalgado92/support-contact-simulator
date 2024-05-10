from agent_simulator.elements.Event import Event
from agent_simulator.elements.Contact import Contact
from agent_simulator.elements.Line import Line
from agent_simulator.elements.Agent import Agent

from agent_simulator.collections.AgentPool import AgentPool
from agent_simulator.collections.EventQueue import EventQueue

import numpy as np
import random, bisect

class AgentSimulation:
    def __init__(
        self,
        contact_types:dict = None
    ):
        #Attributes
        self.contact_types=contact_types if contact_types else dict()
        self.agent_pool = AgentPool()
        self.agent_io_queue = None

        #Simulation Carries
        self.arrival_queue = EventQueue(fifo=True)
        self.handling_queue = EventQueue(fifo=False)
        self.waiting_queue = EventQueue(fifo=True)
        
        #Outputs
        self.handled_contacts = list() # of Contacts
        self.missed_contacts = list() # of Contacts

    # Reset
    def reset_simulation(self):
        self.waiting = EventQueue(fifo=True)
        self.handling_queue = EventQueue(fifo=False)
        self.arrival_queue = EventQueue(fifo=False)
        self.handled_contacts = []
        self.missed_contacts = []

    def reset_agents(self):
        self.agent_pool.reset()
        self.agent_io_queue = None
        
    def get_handled(self) -> list:
        return [r.to_dict() for r in self.handled_contacts]
    
    def get_missed(self) -> list:
        return [r.to_dict() for r in self.missed_contacts]
    
    def get_solved(self) -> list:
        return [*self.get_handled(),*self.get_missed()] 
         
    # Add and Remove Contact Types
    def add_contact_type(
        self, 
        name:str, 
        base:float,
        increment:float,
        average_patience:float = None, 
        auto_solve_time:float = None
    ) -> None:
        """
            Usage: Create a contact type.
            Arguments:
            -name: must be unique within contact_types, will overwrite otherwise.
            -base: must be a float bigger than 0 (part of aht calculation: base + increment x conc)
            -increment: must be a float bigger or equal to 0 (part of aht calculation: base + increment x conc)
            -average_patience: Optional, if ommitted, infinite patience is assumed.
            -auto-solve-time: Optional, if ommitted, no there will be no auto-solves during simulation.
        """
            
        self.contact_types[name] =  {
            'base': base,
            'increment': increment,
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
    
    #SIMULATION PROCESSES
    
    ### MAIN PROCESS: SIMULATE NEXT
    def simulate(self):
        while(1):
            queues = (self.agent_io_queue, self.arrival_queue, self.handling_queue)
            print('(AGENT-IO,ARRIVAL,HANDLING) ->', queues)
        
            next_queue = min(queues, key=lambda q: q.next.time if q.next else float('inf') )
            event = next_queue.next
            if event == None:
                break
            if event.event_type == "arrival":
                self._process_arrival()
            elif event.event_type == "handling":
                self._process_handling()
            else:
                self._process_agent_io()

    ### SUB PROCESS: ARRIVAL
    def _process_arrival(self):
        #Extract Event and Contact
        event = self.arrival_queue.get_next_event()
        present = event.time
        print("Process Arrival at",present, event.item)
        contact = event.item
        ct = contact.contact_type
        ct_aht = self.contact_types.get(ct)
        
        #Find Agent and Line
        agent = self.agent_pool.find_best_avail_agent(ct)
        
        if agent:
            #Materialise Handling
            conc = agent.occupied_lines + 1
            start = present
            aht = agent.performance_factor * (ct_aht.get('base') + (conc - 1) * ct_aht.get('increment'))
            contact.materialise_handling(start, aht, conc)
            
            #Update Handling
            old_aht = ct_aht.get('base') + (agent.occupied_lines - 1) * ct_aht.get('increment')
            new_aht = ct_aht.get('base') + (conc - 1) * ct_aht.get('increment')
            factor = new_aht / old_aht
            lines_to_update = agent.get_occupied_lines()
            for l in lines_to_update:
                l.contact.update_handling(present, factor, conc)
            
            #Occypy Line
            occupied_line = agent.occupy_line(contact)
            
            #Add line to Handling Queue
            handling_event = Event(occupied_line,'handling', time_callback=lambda l: round(l.contact.end_at,2))
            self.handling_queue.add_event(handling_event)
        
        else:
            print("Contact Waiting...")
            waiting_event = Event(contact,'waiting')
            self.waiting_queue.add_event(waiting_event)

    ### SUB PROCESS: HANDLING
    def _process_handling(self)->None:
        #Extract Event, Line and Contact
        event = self.handling_queue.get_next_event()
        present = event.time
        print("Process Handling at",present)
        line = event.item
        agent = line.agent
        contact = line.contact
        ct = contact.contact_type
        ct_aht = self.contact_types.get(ct)
        
        #Free Line
        agent.clear_line(line)
        
        #Add Contact to Handled Contacts
        self.handled_contacts.append({'contact':contact,'agent':agent,'solved_at': present})

        #Update Handling
        conc = agent.occupied_lines
        old_aht = ct_aht.get('base') + (agent.occupied_lines) * ct_aht.get('increment')
        new_aht = ct_aht.get('base') + (conc - 1) * ct_aht.get('increment')
        factor = new_aht / old_aht
        lines_to_update = agent.get_occupied_lines()
        for l in lines_to_update:
                l.contact.update_handling(present, factor, conc)

        self._check_waiting(agent, present)
    
    ### SUB PROCESS: AGENT IO
    def _process_agent_io(self)->None:
        #Extract Event & Agent
        event = self.agent_io_queue.get_next_event()
        type = event.event_type
        present = event.time
        print("Process Agent IO at",present)
        agent = event.item
        if agent == None:
            print(f"Random pick for {type}")
            agent = self.agent_pool.sample_disabled() if type == 'agent-in' else self.agent_pool.find_earliest_in()
    
        #Process Agent Out
        if type == 'agent-out':
            agent.disable_lines()
        
        #Process Agent In
        elif type == 'agent-in':
            agent.enable_lines(time=present)
            #Check Waiting
            self._check_waiting(agent, present)
    
    def _check_waiting(self, agent:Agent, present:int)->None:
        lines = [*agent.lines]
        random.shuffle(lines)
        for line in sorted(lines, key=lambda l:l.priority):
                if (agent.disabled==False) & (line.is_occupied == False) & line.open & ((line.max_occ > agent.occupied_lines) if line.max_occ else True):
                    cond = lambda e: e.item.contact_type  in line.contact_types
                    waiting_event = self.waiting_queue.get_cond_next_event(cond)
                    if bool(waiting_event):
                        #Materialise Handling
                        contact = waiting_event.item
                        ct = contact.contact_type
                        ct_aht = self.contact_types.get(ct)
                        conc = agent.occupied_lines + 1
                        start = present
                        aht = agent.performance_factor * (ct_aht.get('base') + (conc - 1) * ct_aht.get('increment'))
                        contact.materialise_handling(start, aht, conc)
                        
                        #Update Handling
                        old_aht = ct_aht.get('base') + (agent.occupied_lines - 1) * ct_aht.get('increment')
                        new_aht = ct_aht.get('base') + (conc - 1) * ct_aht.get('increment')
                        factor = new_aht / old_aht
                        lines_to_update = agent.get_occupied_lines()
                        for l in lines_to_update:
                            l.contact.update_handling(present, factor, conc)

                        #Occypy Line
                        occupied_line = agent.occupy_line(contact,specific_line=line)
            
                        #Add line to Handling Queue
                        handling_event = Event(line,'handling', time_callback=lambda l: round(l.contact.end_at,2))
                        self.handling_queue.add_event(handling_event)
    

    #AGENT IO QUEUE
    def generate_io_from_coverage(self,coverage:list=[3,2,3], interval:int=60, wrapup:int=0, set:bool=False)->EventQueue:
        """
            Usage: Generate Agent IO events from a list of interval coverages. Random agent IN/OUT events created,
            based solely on the difference between coverage values between consecutive intervals.
            
            Arguments:
                -coverage: list of values for number of active agents on a given interval
                -interval: time period in selected unit
                -wrapup: wrapup time (in same units as interval), agents are disabled this amount of time before the 
                end of the interval where they would be removed. Disabled agents can't get new contacts.
                -set: boolean, sets self's agent IO queue to the function return.
        """
        agent_io_queue = EventQueue(fifo=False)
        max_agents = max(coverage)
        prev = 0
        for idx, cov in enumerate(coverage):
            diff = cov - prev
            ins = 0
            outs = 0
            if diff > 0:
                ins = diff
            else:
                outs = -diff
            for _ in range(outs):
                agent_io_queue.add_event(Event(item=None, event_type='agent-out' ,time=interval * idx - wrapup))
            for _ in range(ins):
                agent_io_queue.add_event(Event(item=None, event_type='agent-in' ,time=interval * idx))
            prev = cov
        if set:
            self.agent_io_queue = agent_io_queue
        return agent_io_queue

    def generate_basic_io(self,ios:list=[(3,0), (2,1) ,(0,2)], interval:int=60, wrapup:int=0, set:bool=False)->EventQueue:
        """
            Usage: Generate Agent IO events from a list of (in,out) tuples. Random agent IN/OUT events created,
            based on tuple values for each interval.
            
            Arguments:
                -ios: list of tuples with INs and OUTs at each interval.
                -interval: time period in selected unit.
                -wrapup: wrapup time (in same units as interval), agents are disabled this amount of time before the 
                end of the interval where they would be removed. Disabled agents can't get new contacts.
        """
        
        agent_io_queue = EventQueue(fifo=False)
        max_agents = max([sum(t[0] for t in ios[:i+1]) - sum(t[1] for t in ios[:i+1]) for i in range(len(ios))])
        for idx, io in enumerate(ios):
            ins = io[0]
            outs = io[1]
            for _ in range(outs):
                agent_io_queue.add_event(Event(item=None, event_type='agent-out' ,time=interval * idx - wrapup))
            for _ in range(ins):
                agent_io_queue.add_event(Event(item=None, event_type='agent-in' ,time=interval * idx))
        if set:
            self.agent_io_queue = agent_io_queue
        return agent_io_queue

    #ARRIVALS
    def add_arrivals(self, volumes:list=[5,10,5], contact_type:str='basic',interval:int=60, attempts:int=4)->EventQueue:
        arrival_queue = self.arrival_queue
        T = interval
        curr_time = 0
        total_volumes = sum(volumes)
        results = []
        for _ in range(attempts):
            arrivals = []
            for idx,f in enumerate(volumes):
                curr_time = T*idx
                average_time_between = T / f    
                while(curr_time < (T * (idx+1))):
                    curr_time = curr_time + np.random.exponential(scale=average_time_between)
                    arrivals.append(curr_time) if curr_time < (T * (idx+1)) else None
            results.append(arrivals)
        best_attempt =  min(results, key=lambda a: abs(len(a) - total_volumes))
        events = []
        for a in best_attempt:   
            e = Event(item=Contact(arrival=a, contact_type=contact_type), event_type='arrival', time_callback=lambda c: c.arrival)
            bisect.insort(events, e, key=lambda e: e.time)
        for e in events:
            arrival_queue.add_event(e)
        arrival_queue.sort()
        return arrival_queue

    def add_agents(self, blueprint:list, num_agents:int=1, performance_callback = lambda:1):
        for _ in range(num_agents):
            self.agent_pool.add_agent(Agent(blueprint, performance_factor=performance_callback()))
        return self.agent_pool
    
#    #SIMULATION ITERATORS
#    def coverage_test(self, volumes:dict, lines:int, intervals:int=10) -> None:
#        """
#            Usage: This test will perform the simulation for a set amount of consecutive intervals, 
#            with a fixed number of lines and volumes. This is useful to understand the equilibrium 
#            state of this specific level of coverage for a certain amount of traffic.
#            
#            Arguments:
#            -volumes: Volumes dictionary. Direct input for the 'simulate' method.
#            -lines: Lines available to answer contacts. Direct input for the 'simulate' methiod.
#            -intervals: Number of consecutive intervals (iterations) to simulate.
#        """
#        
#        self.reset()
#        for _ in range(intervals):
#            self.simulate(volumes, lines)
#            
#    def transition_test(self, volumes_start:dict, volumes_end:dict, lines_start:int, lines_end:int, intervals_start:int=10, intervals_end:int=1) -> None:
#        """
#            Usage: This test will perform the a 2-staged simulation. First will perform the sumulation with 'volumes_start' 
#            and 'lines_start' for 'intervals_start' amount of intervals. Consecutively will simulate with 'volumes_end' and 
#            'lines_end' for 'intervals_end' amount of intervals.
#            
#            Arguments:
#            -volumes_start: Volumes dictionary for 'start' stage. Direct input for the 'simulate' method.
#            -volumes_end: Volumes dictionary for 'end' stage. Direct input for the 'simulate' method.
#            -lines_start: Lines available to answer contacts for 'start' stage. Direct input for the 'simulate' methiod.
#            -lines_end: Lines available to answer contacts for 'end' stage. Direct input for the 'simulate' methiod.
#            -intervals_start: Number of consecutive intervals (iterations) to simulate on 'start' stage.
#            -intervals_end: Number of consecutive intervals (iterations) to simulate on 'end' stage.
#        """
#        
#        self.reset()
#        for _ in range(intervals_start):
#            self.simulate(volumes_start, lines_start)
#        for _ in range(intervals_end):
#            self.simulate(volumes_end, lines_end)
#            
#    #COVERAGE TRANSFORMERS
#    @staticmethod
#    def scale_transform(coverage:np.ndarray, scale_factor:float, unit:float=1) -> np.ndarray:
#        """
#            Usage: Used to scale a coverage array by 'scale_factor'.
#        """
#        return np.round(coverage * scale_factor / unit) * unit
#    
#    @staticmethod
#    def shrinkage_transform(coverage:np.ndarray, shrinkage:np.ndarray) -> np.ndarray:
#        """
#            Usage: Used to apply a 'shrinkage' percetage value for every element of 'coverage'.
#            Arrays must have same shape. A value of 0.05 on 'shrinkage' array will produce an output,
#            on the same position, equal to 95% of the value of 'coverage'. 
#            A negative value will output 105%.
#        """
#        if coverage.shape != shrinkage_array.shape:
#            print("ValErr: Arguments 'coverage' and 'shrinkage' must have same shape.")
#            return
#        else:
#            return coverage * (1-shrinkage)
#    
#    @staticmethod
#    def t_smooth_transform(coverage:np.ndarray, smooth_factor:int=2, unit:float=1) -> np.ndarray:
#        """
#            Usage: Will transform 'coverage' with a transition smoothing algorythm. Smaller 'smooth_factor's
#            will lead to bigger effects, with the lower limit being 1. This edge case will simply subtract the 
#            differences array.
#            
#            Arguments:
#            -smooth_factor: Main parameter for the smoothing algorythm. Positive Integer.
#            -unit: Minimum unit size for the differences applied. Will be used for rounding purposes
#        """
#        if smooth_factor <= 0:
#            print("ValErr: Argument 'smooth_factor' must be a positive integer.")
#            return
#        else:
#            
#            diffs = np.array([0, * np.diff(coverage)])
#            return np.round((coverage - diffs / smooth_factor)/unit) * unit
#        
#    @staticmethod
#    def f_log_transform(coverage:np.ndarray, power:float=2.0, threshold:int=5, unit:float=1) -> np.ndarray:
#        """
#            Usage: Will transform 'coverage' by applying a pseudo-filter. This transform is useful to treat coverages 
#            generated by Erlang models. The need for this transform comes from the somewhat conservative values at high
#            traffic intervals. This transform may also increase the low traffic coverage as they pose higher risk of
#            underperformance.
#            
#            Values bellow 'threshold' may only be increased, and the ones over the threshold may only be decreased.
#            The effect will be proportionally regulated by 'power' and finally rounded to the 'unit'.
#        """
#        
#        return coverage - np.round(power * np.log(coverage / threshold) / unit) * unit