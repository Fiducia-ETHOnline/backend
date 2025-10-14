from uagents import Context, Model, Protocol
 

class A2AContext(Model):
    messages:list[dict[str,str]]

class A2AResponse(Model):
    type:str
    content:str

def A2AWalletPacket(address:str):
    return {'role':'wallet','content':address}

def A2AErrorPacket(info):
    return A2AResponse('error',info)

def A2AProposePacket(desc:str,price:float,cid:str,offerId:str,wallet:str):
    return A2AResponse('propose',{
        'desc':desc,
        'price':price,
        'cid':cid,
        'offerId':offerId,
        'wallet':wallet
    })