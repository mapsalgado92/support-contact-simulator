import uuid
import random
from .Line import Line
from .Contact import Contact
from typing import List
from collections import Counter

class Agent:
    def __init__(
        self,
        blueprint:List[dict] = {'num_lines': 1, 'contact_types': ['basic'], 'priority':1, 'max_occ':None},
        performance_factor:float = 1.0,
        max_occ:int = None,
        alias:str = None
    ) -> None:
        self.id = str(uuid.uuid4())
        self.alias = alias
        self.blueprint = blueprint
        self.performance_factor = performance_factor
        self.occupied_lines = 0
        self.lines = self._create_lines(blueprint)
        self.max_occ = max_occ if max_occ else len(self.lines)
        self.disabled = True
        self.last_in = 0

    def _create_lines(self, blueprint: List[dict]) -> List[Line]:
        lines = []
        for item in blueprint:
            num_lines = item.get('num_lines', 1)
            contact_types = item.get('contact_types', [])
            priority = item.get('priority', 1)
            max_occ = item.get('max_occ', None)
            lines.extend([Line( contact_types,lambda: self , priority, max_occ) for _ in range(num_lines)])
        return lines

    def occupy_line(self, contact:Contact, specific_line:Line = None)->Line:
        self.occupied_lines += 1
        selected_line = specific_line
        if(specific_line == None):
            ct = contact.contact_type
            avail_lines = [line for line in self.lines if (line.is_occupied == False) & (ct in line.contact_types)]
            selected_line = min(avail_lines, key = lambda l: l.priority) 
        selected_line.occupy(contact)
        return selected_line
    
    def clear_line(self, line)->Line:
        self.occupied_lines -= 1
        line.solve()
        return line

    def disable_lines(self)->"Agent":
        if self.disabled: 
            print('Agent | Agent already disabled.')
        else:
            [line.disable() for line in self.lines]
            self.disabled = True
        return self
            
    def enable_lines(self, time:float=0)->"Agent":
        if self.disabled:
            [line.enable() for line in self.lines]
            self.disabled = False
            self.last_in = time
        else:
            print('Agent | Agent not disabled.')
        return self

    def get_availability(self):
        if self.disabled | (self.occupied_lines==self.max_occ):
            return {}
        else:
            open_contact_types = [
                contact_type 
                for line 
                in self.lines 
                if (line.open 
                    & (line.is_occupied == False) 
                    & (self.occupied_lines < (line.max_occ if line.max_occ else float('inf')))
                   )
                for contact_type 
                in line.contact_types
            ]
            return dict(Counter(open_contact_types))

    def get_occupied_lines(self):
        return [line for line in self.lines if line.is_occupied]
            
    def __repr__(self):
        return f"Agent(availability={self.get_availability()}{f', alias={self.alias}' if self.alias else ''})"

    
    