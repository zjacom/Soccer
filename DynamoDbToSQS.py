import boto3
import json

def lambda_handler(event, context):
    sqs_queue_url = [SQS URL]
    stream_arn = [DynamoDB Stream ARN]
    dynamodb_client = boto3.client('dynamodb')
    streams_client = boto3.client('dynamodbstreams')

    sqs_client = boto3.client('sqs', region_name='ap-northeast-2')
    
    for record in event['Records']:
        # DynamoDB Stream에서 데이터 추출
        if record['eventName'] == 'INSERT':
            # INSERT 이벤트가 발생한 경우에만 처리
            new_image = record['dynamodb']['NewImage']['Time']['S']
            
            # 메시지 내용 생성 (JSON 형식)
            message_body = json.dumps(new_image)
            
            # SQS에 메시지 전송
            response = sqs_client.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=message_body
            )
    
    return {
    'statusCode': 200,
    'body': 'Complete!'
    }
