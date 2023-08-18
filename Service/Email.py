from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

class Email():
    def sendMail(self, subject, message):
        msg = MIMEMultipart()
        msg['From'] = 'drick35@gmail.com'
        msg['To'] = 'drick35@gmail.com'
        msg['Subject'] = subject
        message = message
        msg.attach(MIMEText(message))
        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('drick35@gmail.com', 'hdfykpdsoireyedl')
        mailserver.sendmail('drick35@gmail.com', 'drick35@gmail.com', msg.as_string())
        mailserver.quit()
        pass
