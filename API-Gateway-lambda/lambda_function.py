from __future__ import print_function
import json
import requests
import boto3

client = boto3.client('lex-runtime')
lambdaclient = boto3.client('lambda')
VERIFY_TOKEN='*'
PAGE_ACCESS='*'

def find_item(obj, key):
    item = None
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = find_item(v, key)
            if item is not None:
                return item

##recursivley check for items in a dict given key
def keys_exist(obj, keys):
    for key in keys:
        if find_item(obj, key) is None:
            return(False)
    return(True)
## post request to Lex runtime 
def post_to_lex(send_id,msg_txt):
    apiresponse = client.post_text(
    botName='DHLitNow',
    botAlias='DHLitNowDev',
    userId=send_id,
    sessionAttributes={},
    inputText=msg_txt
    )
    print("lex response:")
    print(apiresponse)
    return(apiresponse)
##send txt via messenger to id
def send_message_attach(send_id, msg_atach_url):
    cvresponse = lambdaclient.invoke(
    FunctionName='OpenCVLambda',
    InvocationType='RequestResponse',
    LogType='Tail',
    #ClientContext='apiinvoke',
    Payload=json.dumps({"url":msg_atach_url})
    )
    print(json.dumps({"url":msg_atach_url}))
    print("opencv response:")
    #print(cvresponse['Payload'].read().decode())
    print("response received")
    resp = cvresponse['Payload']
    resp2 = resp.read()
    resp2 = resp2.decode()
    print(resp2)
    print("response converted")
    params  = {"access_token": PAGE_ACCESS}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": send_id},
                       "message": {"text": resp2}})
    print(data)                   
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
def send_message(send_id, msg_txt):
    response = post_to_lex(send_id,msg_txt)
    params  = {"access_token": PAGE_ACCESS}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": send_id},
                       "message": {"text": response['message']}})
    print(data)                   
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
def lambda_handler(event, context):
    #debug
    print("received event:" )
    print(event)
    #print("Received context:")
    #print(context)
    #print("received Api Id :")
    #event['params']['api-id']
    #handle webhook challenge
    if keys_exist(event, ["params","querystring","hub.verify_token","hub.challenge"]):
        v_token   = str(find_item(event, 'hub.verify_token'))
        challenge = int(find_item(event, 'hub.challenge'))
        if (VERIFY_TOKEN == v_token):
            return(challenge)

    #handle messaging events
    if keys_exist(event, ['body-json','entry']):
        event_entry0 = event['body-json']['entry'][0]
        #print(event_entry0)
        if keys_exist(event_entry0, ['messaging']):
            messaging_event = event_entry0['messaging'][0]
            #print(messaging_event)
            msg_txt = ''
            msg_atach_url = ''
            if keys_exist(messaging_event, ['text']):
                msg_txt   = messaging_event['message']['text']
                msg_atach_url = ''
            if keys_exist(messaging_event, ['attachments']):
                msg_atach = messaging_event['message']['attachments'][0]
                msg_atach_url = msg_atach['payload']['url']  
                msg_txt = ''
            #print(msg_txt)
            sender_id = messaging_event['sender']['id']
            
            #first_word = msg_txt.split(" ")[0]
            
            #if first_word == "!echo":
            if len(msg_txt) > 0:
                print("text flow")
                send_message(sender_id, msg_txt)
            else:
                print("image flow")
                send_message_attach(sender_id,msg_atach_url)
                