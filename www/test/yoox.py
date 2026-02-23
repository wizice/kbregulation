import smtplib 
from email.mime.text import MIMEText 
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
import time

def sendMail(subject, body): 
    msg = MIMEText(body) 
    msg['Subject'] = subject 
    msg['From'] = 'ji972hs@naver.com' 
    msg['To'] = 'clsrndnflsms@gmail.com' 

    naver_server = smtplib.SMTP_SSL('smtp.naver.com', 465) 
    naver_server.login('ji972hs', 'wlgpfudrnr11@8') 
    naver_server.sendmail('ji972hs@naver.com', 'yunjordon@gmail.com', msg.as_string()) 
    naver_server.quit() 
    
    return ""
    
fullUrl = "https://www.yoox.com/kr/42801904KF/item#dept=men&sts=sr_men80_m&cod10=42801904KF&sizeId=6&sizeName=32W-32L"
req = Request(fullUrl, headers={'User-Agent': 'Mozilla/5.0'})
response = BeautifulSoup(urlopen(req))
find_div = response.find("div", {"class":"box-highlighted"})

if(find_div == None):
    sendMail("Buy Now!", "According to https://www.yoox.com/kr/42801904KF/item#dept=men&sts=sr_men80_m&cod10=42801904KF&sizeId=6&sizeName=32W-32L !")
else: 
    find_text = find_div.get_text()
