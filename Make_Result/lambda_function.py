from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import boto3,json
from bs4 import BeautifulSoup
from decimal import Decimal
import datetime
from dateutil import parser
import pytz

kst = pytz.timezone('Asia/Seoul')

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

    def get_time_data(self):
        temp = []
        data = self.table.scan()
        times = data['Items']
        for h in times:
            temp.append(h['Time'])
        return set(temp)
    
    def get_home_odds(self, hometeam):
        data = self.table.scan()
        homes = data['Items']
        for h in homes:
            if h['Home'] == hometeam:
                return float(h['HomeOdds'])
        
    def get_away_odds(self, hometeam):
        data = self.table.scan()
        homes = data['Items']
        for h in homes:
            if h['Home'] == hometeam:
                return float(h['AwayOdds'])
                
    def delete_game(self, home, time):
        try:
            self.table.delete_item(Key={'Home': home, "Time" : time})
        except:
            print("fail")
            raise
    
def lambda_handler(event, context):
    db_access = DatabaseAccess([DynamoDB 테이블 이름])
    
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
    
    # 크롤링할 축구 리그
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
            current_time = datetime.datetime.now(kst) + datetime.timedelta(minutes=5)
            current_time = current_time.strftime('%Y-%m-%d %H:%M')
            
            # 크롤링한 경기가 DB에 있고
            # 만약 해당 경기의 시작 시간이 current_time과 같다면
            if (hometeam_info[0].get_text() in db_access.get_home_data()) and (current_time in db_access.get_time_data()):
                # 배당 차이 계산 후 조건에 맞는다면
                before_home_odd, before_away_odd = db_access.get_home_odds(hometeam_info[0].get_text()), db_access.get_away_odds(hometeam_info[0].get_text())
                after_home_odd, after_away_odd = odds_change_to_float(hometeam_info[1].get_text()), odds_change_to_float(awayteam_info[0].get_text())
                if before_home_odd - after_home_odd >= 0.26:
                    # 해당 아이템 DB에서 삭제
                    db_access.delete_game(hometeam_info[0].get_text(), (date + start_time).rstrip())
                    # 알람 발송
                    client = boto3.client("ses")
                    subject = "배당 하락 감지 알림 서비스 " + "(" + (date + start_time).rstrip() + ")"
                    body = hometeam_info[0].get_text() + " vs " + awayteam_info[1].get_text() + "$" + hometeam_info[0].get_text() + " 배당 변경!" + "$ * " + str(before_home_odd) + " -> " + str(after_home_odd) + " *"
                    message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}
                    response = client.send_email(Source = [이메일 주소], Destination = {"ToAddresses": [이메일 주소]}, Message = message)
                elif before_away_odd - after_away_odd >= 0.26:
                    # 해당 아이템 DB에서 삭제
                    db_access.delete_game(hometeam_info[0].get_text(), (date + start_time).rstrip())
                    # 알람 발송
                    client = boto3.client("ses")
                    subject = "배당 하락 감지 알림 서비스 " + "(" + (date + start_time).rstrip() + ")"
                    body = hometeam_info[0].get_text() + " vs " + awayteam_info[1].get_text() + "$" + awayteam_info[1].get_text() + " 배당 변경!" + "$ * " + str(before_away_odd) + " -> " + str(after_away_odd) + " "
                    message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}
                    response = client.send_email(Source = [이메일 주소], Destination = {"ToAddresses": [이메일 주소]}, Message = message)
                else:
                    db_access.delete_game(hometeam_info[0].get_text(), (date + start_time).rstrip())
                    ele.next_sibling
            else:
                ele.next_sibling
    driver.close()

    
    return {
        'statusCode': 200,
        'body': json.dumps('Data update has been completed!')
    }