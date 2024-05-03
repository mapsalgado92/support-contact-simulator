from .Contact import Contact
from typing import Callable


class Line:
    def __init__(
        self,
        contact_types,
        agent_callback:Callable = lambda:None,
        priority:int = 1,
        max_occ:int = None
    ) -> None:
        self.is_occupied = False
        self.contact_types = contact_types
        self.contact:Contact = None
        self.open = False
        self.priority = priority
        self.max_occ = max_occ
        self.agent_callback = agent_callback

    def occupy(self, contact:Contact)->"Line":
        if self.is_occupied:
            print("Line | Line already occupied.")
        elif contact.contact_type in self.contact_types:
            self.is_occupied = True
            self.contact = contact
        else: 
            print("Line | Invalid contact type.")
        return self

    def solve(self)->Contact:
        if self.is_occupied:
            self.is_occupied = False
            self.contact = None
        else:
            print("Line | No contact to solve.")
        return self
        
    def disable(self)->"Line":
        if self.open:
            self.open = False
        else:
            print("Line | Line already disabled.")
        return self
    
    def enable(self)->"Line":
        if self.open:
            print("Line | Line already enabled.")
        else:
            self.open = True
        return self

    @property
    def agent(self)->"Agent":
        return self.agent_callback()

    def __repr__(self):
        return f"Line(is_occupied={self.is_occupied},open={self.open})"
    