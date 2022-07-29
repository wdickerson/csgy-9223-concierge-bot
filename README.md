# CSGY 9223 Concierge Bot assignment

A chatbot application that gives users restaurant recommendations based on their preferences.

## Frontend

Just a static site in the `frontend` folder. It uses an API Gateway generated SDK and is hosted on S3.

## Lambda functions

`concierge-lf0` handles the API interaction and calls an AWS Lex instance.

`concierge-lf1` is called by Lex to validate user input and place a job in a work queue.

`concierge-lf2` polls the work queue, search ElasticSearch and DynamoDB, and emails the user with results.

## Infrastructure dependencies

S3 to host the frontend.

API Gateway to handle the HTTP endpoints.

The Lambdas mentioned above.

ElasticSearch to hold restaurants with their cuisine types.

DynamoDB to hold more restaurant details.

Lex to handle the chat interactions.

SQS to serve as the work queue.

CloudWatch to repeatedly trigger `concierge-lf2` (so that it may poll the queue).

SES to send emails to the user.

