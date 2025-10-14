from uagents import Context, Model, Protocol
 

class A2AContext(Model):
    messages:list[dict[str,str]]

class A2AResponse(Model):
    type:str
    content:str