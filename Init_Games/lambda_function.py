import json
from decimal import Decimal
from database_access import Database_Access
from chrome_driver import Chrome_Driver

# 크롤링 후 문자열로 되어있는 배당을 float으로 변경하는 함수
def odds_change_to_float(s):
        character_to_remove="[] "
        for x in character_to_remove:
            s = s.replace(x, "")
        s=float(s)
        return s

def lambda_handler(event, lambda_context):
    url = 'https://www.livescore.co.kr/#/sports/score_board/soccer_score.php'
    db_access = Database_Access([DynamoDB 테이블 이름])
    soup = Chrome_Driver.create_soup(url)
    
    # 크롤링할 축구 리그
    target_games = ["UEFA EL", "UEFA ECL", "ENG PR", "GER D1", "ITA D1", "SPA D1", "UEFA CL", "UEFA YL", "FRA D1", "ENG LCH", "AUS D1", "UEFA EURO", "TUR D1", "HOL D1"]

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
                # 배당이 1.99 이상 2.4 이하인 축구 경기만 DB에 저장
                if (1.99 <= odds_change_to_float(hometeam_info[1].get_text()) <= 2.4) or (1.99 <= odds_change_to_float(awayteam_info[0].get_text()) <= 2.4):
                    new_data = {'Time' : (date + start_time).rstrip(),'Home': hometeam_info[0].get_text(), 'HomeOdds' : odds_change_to_float(hometeam_info[1].get_text()), 'AwayOdds' : odds_change_to_float(awayteam_info[0].get_text())}
                    ddb_data = json.loads(json.dumps(new_data), parse_float=Decimal)
                    db_access.put_data(ddb_data)
                else:
                    ele.next_sibling

    
    return {
        'statusCode': 200,
        'body': json.dumps('Soccer Data update has been completed!')
    }