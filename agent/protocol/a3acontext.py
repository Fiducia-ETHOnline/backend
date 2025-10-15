from uagents import Context, Model, Protocol
from uagents_core.protocol import ProtocolSpecification
import json
class A3AContext(Model):
    messages:list[dict[str,str]]

class A3AResponse(Model):
    type:str
    content:str

    

def A3AWalletPacket(address:str):
    return {'role':'wallet','content':address}

def A3AErrorPacket(info):
    return A3AResponse(type='error',content= info)
def A3ATXHashPacket(hash):
    return A3AResponse(type='hash',content=hash)

def A3AProposeCtx(desc:str,price:float,cid:str,offerId:str,wallet:str):
    return A3AContext(messages=[{'role':'answer_order','content':json.dumps({
        'desc':desc,
        'price':price,
        'cid':cid,
        'orderId':offerId,
        'wallet':wallet
    })}])

def create_a3a_protocol():
    return Protocol("A3A Chat Protocol",'1.0')