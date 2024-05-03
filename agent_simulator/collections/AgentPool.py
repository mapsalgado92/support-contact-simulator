import random
from ..elements.Agent import Agent

class AgentPool:
    def __init__(self, agents:list = None):
        self.agents = agents if agents else list()

    def add_agent(self, agent:Agent)->"AgentPool":
        self.agents.append(agent)

    def reset(self):
        self.agents = list()

    def sample_disabled(self) -> Agent:
        return random.choice([a for a in self.agents if a.disabled])
    
    def sample_enabled(self) -> Agent:
        return random.choice([a for a in self.agents if not a.disabled])

    def find_earliest_in(self) -> Agent:
        return min([a for a in self.agents if not a.disabled], key=lambda a: a.last_in)
        
    def find_agent_by_id(self, id:str) -> Agent:
        next((a for a in self.agents if a.id == id), None)

    def find_best_avail_agent(self, contact_type:str) -> Agent:
        avail_agents = [agent for agent in self.agents if (agent.get_availability().get(contact_type, 0) > 0)]
        if len(avail_agents) == 0:
            return None
        else:
            return min(avail_agents,key=lambda a: a.occupied_lines)

    @property
    def size(self) -> int:
        return len(self.agents)
    @property
    def active(self) -> int:
        return len([1 for agent in self.agents if agent.disabled == False])

    def __repr__(self):
        return f"AgentPool(size={self.size},active={self.active})"

   