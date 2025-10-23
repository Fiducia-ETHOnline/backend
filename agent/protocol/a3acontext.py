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
    cid:str

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
def A3AWalletResponse(address:str):
    return A3AResponse(type='wallet',content=address)
def A3AErrorPacket(info):
    return A3AResponse(type='error',content= info)
def A3ATXHashPacket(hash):
    return A3AResponse(type='hash',content=hash)
def A3AMerchantWalletQuery(merchant_id: str | None = None):
    """Build a query to fetch the merchant's payout wallet.

    If merchant_id is provided, include a scoping hint so the merchant agent
    returns data for that merchant specifically.
    """
    msgs: list[A3AMessage] = []
    if merchant_id:
        msgs.append(A3AMessage(role='agent', content=f'merchant_id:{merchant_id}'))
    msgs.append(A3AMessage(role='query_wallet', content=''))
    return A3AContext(messages=msgs)

def A3AMerchantMenuQuery(merchant_id: str | None = None):
    """Build a query to fetch the merchant's live menu.

    If merchant_id is provided, include a scoping hint so the merchant agent
    returns data for that merchant specifically.
    """
    msgs: list[A3AMessage] = []
    if merchant_id:
        msgs.append(A3AMessage(role='agent', content=f'merchant_id:{merchant_id}'))
    msgs.append(A3AMessage(role='query_menu', content=''))
    return A3AContext(messages=msgs)
def A3AMenuResponse(menu_lines:str):
    # menu_lines is a pre-formatted string like "- item: $price\n- item2: $price2"
    return A3AResponse(type='menu', content=menu_lines)
def A3AProposeCtx(desc:str,price:str,cid:str,offerId:str,wallet:str):
    return A3AContext(messages=[A3AMessage(role='answer_order',content= A3ACustomerProposeRequest(desc=desc,
                                                          price=price,
                                                          cid=cid,
                                                          orderId=offerId,
                                                          wallet=wallet))]
    )
def A3AOrderResponse(orderid:str,desc:str,price:str,unsigned_transaction:str,cid:str):
    return A3AResponse(type='order',content= A3ACustomerOrderResponse(orderId=orderid,price=price,desc=desc,transaction=unsigned_transaction,cid=cid))
def create_a3a_protocol():
    return Protocol("A3A Chat Protocol",'1.0')