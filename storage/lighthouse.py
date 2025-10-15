import io,json,asyncio
from lighthouseweb3 import Lighthouse
import base64
from multiformats import *
# Replace "YOUR_API_TOKEN" with your actual Lighthouse API token
lh = Lighthouse(token="fe3ea12e.a26d106bd2e74aeaaf314d522d331385")

def upload_order_desc(info,filename):
    resp =lh.uploadBlob(io.BytesIO(json.dumps(info).encode('utf-8')),filename)
    return resp['data']['Hash']


def CID2Digest(cid:str):
    cid_decoded =CID.decode(cid)
    # print(cid_decoded.base)
    # print(cid_decoded.codec)
    # print(cid_decoded.hashfun)
    # print(cid_decoded.digest)
    return cid_decoded.raw_digest.hex()

def CIDRebuild(digest:str):
    cid = CID(multibase.get('base32'),1,multicodec.multicodec('raw', tag='ipld'),multihash.wrap(
        bytes.fromhex(digest),
        hashfun='sha2-256'
    ))
    return cid
    
# print(CID2Digest('bafkreidm2z6jwkqkihvajtjfrmjf43hxrju2e75fbfb27x3ufy3cioreem'))