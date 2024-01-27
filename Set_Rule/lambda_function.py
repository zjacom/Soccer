import json
import boto3
import random
import datetime
import time

def create_cloudwatch_event(time_str, rule_name, target_arn):
    # CloudWatch Events 클라이언트 생성
    cloudwatch_events = boto3.client('events', region_name='ap-northeast-2')

    # 문자열을 날짜 및 시간 객체로 변환
    scheduled_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M') - datetime.timedelta(minutes=545)

    # CloudWatch Events 규칙 생성
    response = cloudwatch_events.put_rule(
        Name=rule_name,
        ScheduleExpression=f'cron({scheduled_time.minute} {scheduled_time.hour} {scheduled_time.day} {scheduled_time.month} ? {scheduled_time.year})',
        State='ENABLED'
    )

    # 규칙과 연결할 경기 시작 5분전 배당 확인 후 알람 서비스
    
    # id_num 랜덤 배정
    id_num = str(random.randint(1, 1000))

    # CloudWatch Events 규칙과 대상 연결
    cloudwatch_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Id': id_num,
                'Arn': target_arn
            }
        ]
    )
    print("Complete create Rule!")

def update_lambda_trigger(rule_name, target_arn, events_client):
    # Lambda 및 CloudWatch Events 클라이언트 생성
    lambda_client = boto3.client('lambda', region_name='ap-northeast-2')
    
    # CloudWatch Events 규칙의 ARN 가져오기
    response = events_client.describe_rule(Name=rule_name)
    rule_arn = response['Arn']
    
    # 대상 람다 함수에 대한 권한 설정
    lambda_client.add_permission(
        FunctionName=target_arn,
        StatementId=f'{rule_name}-Permission',
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_arn
    )
    
# cron 표현식으로 변환

def str_to_cron(input_datetime_str):
    input_datetime = datetime.datetime.strptime(input_datetime_str, '%Y-%m-%d %H:%M') - datetime.timedelta(minutes=545)
    
    # cron 표현식으로 변환
    cron_expression = f'{input_datetime.minute} {input_datetime.hour} {input_datetime.day} {input_datetime.month} ? {input_datetime.year}'
    
    return cron_expression

def clean_cron_expression(cron_expression):
    return cron_expression.replace('cron', '').replace('(', '').replace(')', '')

def lambda_handler(event, context):
    # SQS 대기열 URL 설정
    sqs_queue_url = [SQS URL]
    target_arn = [Make_Result Lambda Function ARN]
    
    # SQS 클라이언트 생성
    sqs_client = boto3.client('sqs', region_name='ap-northeast-2')
    
    events_client = boto3.client('events', region_name='ap-northeast-2')

    # 여기서는 모든 규칙을 가져옵니다.
    response = events_client.list_rules()
    
    # 규칙 목록을 저장할 리스트를 생성합니다.
    cron_expressions = []
    
    # 규칙 목록을 반복하면서 Cron 표현식을 추출합니다.
    for rule in response['Rules']:
        if 'ScheduleExpression' in rule:
            cron_expression = rule['ScheduleExpression']
            cron_expressions.append(cron_expression)

    # 모든 원소에 함수를 적용하여 새로운 배열 생성
    cleaned_expressions = [clean_cron_expression(expression) for expression in cron_expressions]
    
    # SQS 대기열로부터 메시지 가져오기
    response = sqs_client.receive_message(
        QueueUrl=sqs_queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=30,
        WaitTimeSeconds=20
    )
    
    if 'Messages' in response:
        for message in response['Messages']:
            # 메시지 내용 추출 (JSON 형식)
            time = json.loads(message['Body'])
            
            
            if str_to_cron(time) not in cleaned_expressions:
                current_time = datetime.datetime.now()
                rule_name = f"my_rule_{current_time.strftime('%Y%m%d%H%M%S')}"
                create_cloudwatch_event(time, rule_name, target_arn)
                update_lambda_trigger(rule_name, target_arn, events_client)
            
            
            # SQS 대기열에서 메시지 삭제
            receipt_handle = message['ReceiptHandle']
            
            sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=receipt_handle
            )
            print("Message deleted.")
    else:
        print("No messages in the queue.")

    return {
        'statusCode': 200,
        'body': 'Message handling completed.'
    }
