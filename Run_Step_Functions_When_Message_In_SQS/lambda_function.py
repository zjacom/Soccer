import json
import boto3

def lambda_handler(event, context):
    # SQS 큐 URL 및 Step Functions ARN 설정
    sqs_queue_url = [SQS URL]
    step_functions_arn = [Step Functions ARN]

    # SQS 메시지 처리
    sqs = boto3.client('sqs')
    messages = sqs.receive_message(QueueUrl=sqs_queue_url, MaxNumberOfMessages=1)

    if 'Messages' in messages:
        # Step Functions 실행
        sf_client = boto3.client('stepfunctions')
        sf_client.start_execution(
            stateMachineArn=step_functions_arn
        )
    
    return {
        'statusCode': 200,
        'body': 'Lambda execution completed.'
    }
