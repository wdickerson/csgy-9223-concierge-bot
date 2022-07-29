import json
import boto3
import requests
import os

sqs = boto3.resource('sqs')
ses_client = boto3.client('ses')
dynamo_client = boto3.client('dynamodb')

es_url = '<ENTER>'


def lambda_handler(event, context):
    """
    Requests messages from an SQS queue.
    If messages recieved, for each message:
    -Query elasticsearch for restaurants
    -Get restaurant data from dynamodb
    -Send email with SES
    -Delete the message from the queue
    """
    queue = sqs.get_queue_by_name(QueueName='concierge-q1')
    
    sqs_response = queue.receive_messages(
        MessageAttributeNames=[ 'All' ],
        MaxNumberOfMessages=3,
    )
    
    for message in sqs_response:
        print(json.dumps(message.message_attributes))
        message_attrs = message.message_attributes
        attrs = {
            'cuisine': message_attrs['cuisine']['StringValue'],
            'party_size': message_attrs['party_size']['StringValue'],
            'dining_time': message_attrs['dining_time']['StringValue'],
            'email': message_attrs['email']['StringValue'],
        }
        
        # Craft an es query based on users input
        query = {
            "size": 5,
            "query": {
                "function_score": {
                    "query": {
                        "term": {
                            "cuisines": attrs['cuisine'].lower()
                        }
                    },
                    "random_score": {}
                }
            }
        }
    
        headers = { 
            "Content-Type": "application/json",
            "Authorization": "Basic " + os.environ['ES_KEY'],
        }
    
        # Make the HTTP request to es
        es_response = requests.post(es_url, headers=headers, data=json.dumps(query))
        
        # Default email message if no results found
        html_items = [
            f"<p>I'm sorry, I couldn't find any {attrs['cuisine']} recommendations \
            for {attrs['dining_time']}.<p>"
        ]
        
        # If results found, craft real email message
        if es_response.json()['hits']['total']['value'] > 0:
            # Craft a dynamodb batch query based on the es result
            es_ids = [
                hit['_id']
                for hit in es_response.json()['hits']['hits']
            ]
            
            batch_keys = {
                'yelp-restaurants': {
                    'Keys': [
                        { 'businessId': { 'S': es_id } } 
                        for es_id in es_ids
                    ]
                },
            }
            
            # Get the posts from dynamo and format them
            dynamo_response = dynamo_client.batch_get_item(RequestItems=batch_keys)
            
            restaurants = [{
                'name': record['name']['S'],
                'address': record['location']['M']['address1']['S'],
                'rating': record['rating']['N'],
            } for record in dynamo_response['Responses']['yelp-restaurants']]
            
            html_items = [
                f"<p><strong>{r['name']} ({r['rating']})</strong> {r['address']}<p>"
                for r in restaurants
            ]
            
            intro = '<p>Hello! Here are my recs'
            
            intro = f"Hello! Here are my {attrs['cuisine']} restaurant \
                suggestions for {attrs['party_size']} people, \
                for today at {attrs['dining_time']}:"
            html_items.insert(0, intro)
        
        # Send the email
        ses_client.send_email(
            Source='<ENTER>',
            Destination={
                'ToAddresses': [attrs['email']]
            },
            Message={
                'Subject': {
                    'Data': 'Your results from Cocierge Bot',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': '\n'.join(html_items),
                        'Charset': 'UTF-8'
                    }
                }
            },
            ReplyToAddresses=[
                '<ENTER>',
            ],
            ReturnPath='<ENTER>',        )
        
        # Delete the message from the queue
        queue.delete_messages(
            Entries=[
                {
                    'Id': 'id',
                    'ReceiptHandle': message.receipt_handle
                },
            ]
        )
    
    # Done processing this batch of messages from the queue
    return {}
