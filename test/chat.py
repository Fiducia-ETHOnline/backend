import requests
from utils.authlib import auth_login
import json
auth_res= auth_login()
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}
ctx = []
while True:
    prompt = input("input prompt:")
    ctx.append({
    'role':'user',
    'content':prompt})

    resp= requests.post('http://127.0.0.1:5000/api/chat/messages', json={'messages':ctx
    }, headers=headers) 
    print(resp.json()['content'])
    ctx.append({'role':'assistant','content':resp.json()['content']})
# from uagents import Agent, Context, Model
# class A2AContext(Model):
#     messages:list[dict[str,str]]

# class A2AResponse(Model):
#     type:str
#     content:str
# class WeatherForecastRequest(Model):
#     location: str


# class WeatherForecastResponse(Model):
#     location: str
#     temp: float
#     condition: str
#     humidity: float
#     wind_speed: float
# news_agent_address = "agent1qgr29twm4m9p6j6k8qmd3r23mtg7hck4rwxuyyu42aqcpa7n3mvsx4vl6nl"

# from uagents.query import send_sync_message,query
# class NewsRequest(Model):
#     company_name: str


# class UrlRequest(Model):
#     company_name: str


# class wrapRequest(Model):
#     url: str


# class SentimentRequest(Model):
#     news: str

# async def main():
#     response = await send_sync_message(
#         destination=news_agent_address,
#         message=A2AContext(messages=[{
#     'role':'user',
#     'content':'who are you?'}]),
#         timeout=15.0,
#     )
#     print(response)

# import asyncio
# asyncio.run(main())
