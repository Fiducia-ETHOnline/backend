from uagents import Context, Model, Protocol
from uagents_core.protocol import ProtocolSpecification
import json
from decimal import Decimal
from typing import TypedDict
class A3ACustomerOrderResponse(Model):
    orderId:str
    price:str
    desc:str
    transaction:str

class A3ACustomerProposeRequest(Model):
    desc:str
    price:str
    cid:str
    orderId:str
    wallet:str

class A3AMessage(TypedDict, total = False):
    role:str
    content:str | A3ACustomerProposeRequest


class A3AContext(Model):
    messages:list[A3AMessage]

class A3AResponse(Model):
    type:str
    content:str | A3ACustomerOrderResponse

def A3AWalletPacket(address:str):
    return {'role':'wallet','content':address}

def A3AErrorPacket(info):
    return A3AResponse(type='error',content= info)
def A3ATXHashPacket(hash):
    return A3AResponse(type='hash',content=hash)

def A3AProposeCtx(desc:str,price:str,cid:str,offerId:str,wallet:str):
    return A3AContext(messages=[A3AMessage(role='answer_order',content= A3ACustomerProposeRequest(desc=desc,
                                                          price=price,
                                                          cid=cid,
                                                          orderId=offerId,
                                                          wallet=wallet))]
    )
def A3AOrderResponse(orderid:str,desc:str,price:str,unsigned_transaction:str):
    return A3AResponse(type='order',content= A3ACustomerOrderResponse(orderId=orderid,price=price,desc=desc,transaction=unsigned_transaction))
def create_a3a_protocol():
    return Protocol("A3A Chat Protocol",'1.0')