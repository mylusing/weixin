#coding:utf8
import logging
import hashlib
import time
from lxml import etree
import json
import requests
import tornado.ioloop
import tornado.web

logging.basicConfig(level=logging.DEBUG)
token = 'weixintoken'
reply_text = '''<xml>
                    <ToUserName><![CDATA[{toUserName}]]></ToUserName>
                    <FromUserName><![CDATA[{fromUserName}]]></FromUserName>
                    <CreateTime><![CDATA[{createTime}]]></CreateTime>
                    <MsgType><![CDATA[{msgType}]]></MsgType>
                    <Content><![CDATA[{content}]]></Content>
                    <FuncFlag><![CDATA[{funcFlag}]]></FuncFlag>
                    </xml>'''


class WeiXinMessageHandle:
	def __init__(self,xmlString):
		et = etree.fromstring(xmlString)
		self.ToUserName   = et.find('ToUserName').text
		self.FromUserName = et.find('FromUserName').text
		self.MsgType      = et.find('MsgType').text
		self.CreateTime   = et.find('CreateTime').text
		MsgId             = et.find('MsgId').text
		if self.MsgType == 'text':
			self.Content = et.find('Content').text
		elif self.MsgType == "image":
			self.PicUrl = et.find('PicUrl').text
		elif self.MsgType == 'location':
			self.Location_X = et.find('Location_X').text
			self.Location_Y = et.find('Location_Y').text
			self.Scale = et.find('Scale').text
			self.Label = et.find('Label').text
		elif self.MsgType == 'link':
			self.Title = et.find('Title').text
			self.Description = et.find('Description').text
			self.Url = et.find('Url').text

	def handleMessage(self):
		reply = u'默认回复'
		if self.MsgType == 'text':
			if self.Content == 'sj':
				reply = self.currentTime()
			elif self.Content.startswith(u'天气'):
				# reply = u'你是不是想知道天气，我也想知道'
				city  = self.Content[2:].strip()
				reply = self.weather(city)
				logging.info(reply)
		else:
			reply = u'你发的不是文字，老子现在处理不了'
		resultMessage = reply_text.format(
                            toUserName   = self.FromUserName,
                            fromUserName = self.ToUserName,
                            createTime   = str(int(time.time())),
                            msgType      = 'text',
                            content      = reply.encode('utf-8'),
                            funcFlag     = 1,
			)
		return resultMessage

	def currentTime(self):
		t = time.ctime()
		return t.encode('utf-8')

	def weather(self,city):
		url = "http://api.map.baidu.com/telematics/v3/weather?output=json&ak=8a47b6b4cfee5e398e63df510980697e&location="+city.encode('utf-8')
		res = requests.get(url)
		html = res.text
		res.close()
		json_data = json.loads(html)
		error = json_data.get('error')
		if error != 0:
			body = u'不支持该城市'
			return body
		else:
			result = json_data.get('results',u'没有结果')
			weather = result[0]
			c_city = weather.get('currentCity',None)
			weather_data = weather.get('weather_data',None)
			body = u'{0}\n今天：{1},{2},{3}\n明天：{4},{5},{6}'.format(c_city,weather_data[0].get('temperature'),weather_data[0].get('weather'),weather_data[0].get('wind'), \
	                                                weather_data[1].get('temperature'),weather_data[1].get('weather'),weather_data[1].get('wind'))
			return body




class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        checkSignatureResult = self.__checkSignature()
        if checkSignatureResult:
            self.write(checkSignatureResult)
            logging.info("成功接入微信开发平台")
        else:
            logging.info("接入微信平台失败")
            raise tornado.web.HTTPError(status_code=500,log_message="接入微信平台失败" )
        self.finish()

    def __checkSignature(self):
        signature  = self.get_query_argument(name="signature")
        timestamp  = self.get_query_argument(name="timestamp")
        nonce      = self.get_query_argument(name="nonce")
        echostr    = self.get_query_argument(name="echostr",default=False)
        stringList = [ timestamp, nonce, token ]
        stringList.sort(key=None, reverse=False)
        concatenatedString = ''.join(stringList)
        encodedConcatenatedString = concatenatedString.encode()
        sha1Object = hashlib.sha1()
        sha1Object.update(encodedConcatenatedString)
        generated_signature = sha1Object.hexdigest()
        if generated_signature == signature:
            return echostr
        else:
            return None

    def post(self):
        body = self.request.body
        bodyString = body.decode('utf-8')
        logging.info(bodyString)
        # handle message then return
        weixin = WeiXinMessageHandle(bodyString)
        resultMessage = weixin.handleMessage()
        self.set_status(200)
        self.write(resultMessage)
        self.finish()
 
application = tornado.web.Application([
    (r"/", MainHandler),
])
 
if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
