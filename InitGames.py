from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import boto3,json
from bs4 import BeautifulSoup
from decimal import Decimal
import datetime
from dateutil import parser

class DatabaseAccess():
    def __init__(self, TABLE_NAME):
        # DynamoDB 세팅
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(TABLE_NAME)
      
    def get_home_data(self):
        temp = []
        data = self.table.scan()
        homes = data['Items']
        for h in homes:
            temp.append(h['Home'])
        return temp
    
    def put_data(self, input_data):
        self.table.put_item(
            Item =  input_data
        )

def lambda_handler(event, context):
    db_access = DatabaseAccess([DynamoDB 이름])
    
    # 크롬 드라이버 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280x1696')
    chrome_options.add_argument('--user-data-dir=/tmp/user-data')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--log-level=0')
    chrome_options.add_argument('--v=99')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--data-path=/tmp/data-path')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--homedir=/tmp')
    chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

    chrome_options.binary_location = "/opt/python/bin/headless-chromium"
    driver = webdriver.Chrome('/opt/python/bin/chromedriver', chrome_options=chrome_options)
    driver.get('https://www.livescore.co.kr/#/sports/score_board/soccer_score.php')
    
    driver.switch_to.frame('content')
    soup=BeautifulSoup(driver.page_source)
    
    # 알람 받고 싶은 축구 리그 선택
    target_games = ["UEFA EL", "UEFA ECL", "ENG PR", "GER D1", "ITA D1", "SPA D1", "UEFA CL", "UEFA YL", "FRA D1", "ENG LCH", "AUS D1", "UEFA EURO", "TUR D1", "HOL D1"]

    # 크롤링 후 문자열로 되어있는 배당을 float으로 변경하는 함수
    def odds_change_to_float(s):
            character_to_remove="[] "
            for x in character_to_remove:
                s = s.replace(x,"")
            s=float(s)
            return s

    # 축구 경기 요소만 필터링
    soccer_games = soup.find("table", {"border" : "1"}).find("tbody").find_all("tr")

    for ele in soccer_games:
        # 경기 날짜 변수 date에 저장
        if ele.find("strong", {"class" : "th_cal"}) != None:
            date = ele.find("strong", {"class" : "th_cal"}).get_text()
        # 배당이 없는 경기나 target_games에 포함되지 않은 리그는 패스
        elif ele.find("span",{"id" : "odds"}) == None or ele.find("td", {"class" : 'game'}).get_text() not in target_games:
            ele.next_sibling
        # 필요한 정보 추출 후 DB에 저장
        else:
            start_time=ele.find("td",{"class" : "stime"}).get_text()
            hometeam_info=ele.find("td",{"class" : "hometeam"}).find_all("span")
            awayteam_info=ele.find("td",{"class" : "visitor"}).find_all("span")

            # 이미 있는 DB에 저장된 경기라면 패스, 아니라면 새로 업데이트
            if hometeam_info[0].get_text() in db_access.get_home_data():
                ele.next_sibling
            else:
                if (odds_change_to_float(hometeam_info[1].get_text()) <= 2.4) or (odds_change_to_float(awayteam_info[0].get_text()) <= 2.4):
                    new_data = {'Time' : (date + start_time).rstrip(),'Home': hometeam_info[0].get_text(), 'HomeOdds' : odds_change_to_float(hometeam_info[1].get_text()), 'AwayOdds' : odds_change_to_float(awayteam_info[0].get_text())}
                    ddb_data = json.loads(json.dumps(new_data), parse_float=Decimal)
                    db_access.put_data(ddb_data)
                else:
                    ele.next_sibling
    driver.close()

    
    return {
        'statusCode': 200,
        'body': json.dumps('Complete!')
    }
