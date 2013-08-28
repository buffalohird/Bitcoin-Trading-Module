
# Basic MtGox API v2 implementation 
# Some code inspired by http://pastebin.com/aXQfULyq
# Don't request results more often than every 10 seconds, you risk being blocked by the anti-DDoS filters

import time,hmac,base64,hashlib,urllib,urllib2,json,csv,math,sys
from datetime import datetime

class mtgox:
        timeout = 15
        tryout = 8

        def __init__(self, key='key', secret='secret', agent='btc_bot'):
                self.key, self.secret, self.agent = key, secret, agent
                self.time = {'init': time.time(), 'req': time.time()}
                self.reqs = {'max': 10, 'window': 10, 'curr': 0}
                self.base = 'https://data.mtgox.com/api/2/'

        def throttle(self):
                # check that in a given time window (10 seconds),
                # no more than a maximum number of requests (10)
                # have been sent, otherwise sleep for a bit
                diff = time.time() - self.time['req']
                if diff > self.reqs['window']:
                        self.reqs['curr'] = 0
                        self.time['req'] = time.time()
                self.reqs['curr'] += 1
                if self.reqs['curr'] > self.reqs['max']:
                        print 'Request limit reached...'
                        time.sleep(self.reqs['window'] - diff)

        def makereq(self, path, data):
                # bare-bones hmac rest sign
                return urllib2.Request(self.base + path, data, {
                        'User-Agent': self.agent,
                        'Rest-Key': self.key,
                        'Rest-Sign': base64.b64encode(str(hmac.new(base64.b64decode(self.secret), path + chr(0) + data, hashlib.sha512).digest())),
                })

        def req(self, path, inp={}):
                t0 = time.time()
                tries = 0
                while True:
                        # check if have been making too many requests
                        self.throttle()

                        try:
                                # send request to mtgox
                                inp['nonce'] = str(int(time.time() * 1e6))
                                inpstr = urllib.urlencode(inp.items())
                                req = self.makereq(path, inpstr)
                                response = urllib2.urlopen(req, inpstr)

                                # interpret json response
                                output = json.load(response)
                                if 'error' in output:
                                        raise ValueError(output['error'])
                                return output
                                
                        except Exception as e:
                                print "Error: %s" % e

                        # don't wait too long
                        tries += 1
                        if time.time() - t0 > self.timeout or tries > self.tryout:
                                raise Exception('Timeout')
                                
def margin():
  gox = mtgox()
  current_fee = gox.req('BTCUSD/money/info')['data']['Trade_Fee']
  fee_margin = 2 * current_fee / 100
  current_price = gox.req('BTCUSD/money/order/quote', {'type':'bid','amount':100000000})
  current_price_print = current_price['data']['amount'] / 1e5
  current_margin = current_price_print * fee_margin
  margin_high = current_price_print + current_margin
  margin_low = current_price_print - current_margin
  print "1) Current Price of $%f" % (current_price_print)
  print "2) Necessary revenue margin needed for profit: $%f" % (current_margin)
  print "3) Sell now and buy below %f to profit" % (margin_low)
  print "4) Buy now and sell above %f to profit" % (margin_high)

def status_update():
  gox = mtgox()
  current_price = gox.req('BTCUSD/money/order/quote', {'type':'bid','amount':100000000})
  current_price_print = current_price['data']['amount'] / 1e5
  current_lag = gox.req('BTCUSD/money/order/lag')['data']['lag_secs']
  print "1) Current Price of $%f" % (current_price_print)
  print "2) Order lag of %f seconds" % (current_lag)

def mainloop():

  #connect to gox
  gox = mtgox()

  #set up spreadsheet input
  """input_string = "STARTFILE.csv"
  reader = csv.reader(open(input_string, "wb"))
  has_start = False
  for line in reader:
  	has_start = True
  if(has_start):
    print "has_start"
  else:
    print "no start"
  """
  
  #set up spreadsheet output
  file_string = "NEWFILE " + str(datetime.now()) + ".csv"
  writer = csv.writer(open(file_string, "wb"))
  writer.writerow(["Update #", "Current Time", "Current Price (USD)", "Price Change", "Commission Fee (%)"])
  derivatives = [0,0,0,0,0]
  
  #determine fee
  current_fee = gox.req('BTCUSD/money/info')['data']['Trade_Fee']
  
  
  
  update_counter = 0
  previous_price = 1
  previous_time = datetime.now()
  high_point = 1.0
  low_point = 10000.0
  price_change = 0
  price_change_sign = 0
  
  #set up 

  while True:
        current_time = datetime.now()
        print "update #%d (%s):" % (update_counter, current_time)
        try:
                bid_price = gox.req('BTCUSD/money/order/quote', {'type':'bid','amount':100000000})
                bid_price_print = bid_price['data']['amount'] / 1e5
                print "1)  Current USD Bid Price: %f" % (bid_price_print)
                
                #bid_ticker = gox.req('BTCUSD/money/ticker_fast')
                #print json.dumps(bid_ticker, sort_keys=True, indent=4, separators=(',', ': '))
                
                #check highs and lows
                if bid_price_print > high_point:
                	high_point = bid_price_print
                if bid_price_print < low_point:
                	low_point = bid_price_print
                                
                #print the per-turn derivative
                price_change_raw = previous_price - bid_price_print
                price_change = math.fabs(price_change_raw)
                if bid_price_print < previous_price:
                    price_change_sign = -1
                    print "2)  Drop of price by %f (%f percent change)" % (price_change, price_change / previous_price * 100)
                elif bid_price_print > previous_price:
                    price_change_sign = 1
                    print "2)  Rise of price by %f (%f percent change)" % (price_change, price_change / previous_price * 100)
                else:
                    price_change_sign = 1
                    print "2)  No Price Change (0 percent change)"  
                    
                      
                if update_counter % 10 == 0 and update_counter != 0:
                	#print high and low
				    print "3)  High of %f (%f percent change)" % (high_point, high_point / bid_price_print * 100)
				    print "4) Low of %f (%f percent change)" % (low_point, bid_price_print / low_point * 100)
				    #check for fee change
				    new_fee = gox.req('BTCUSD/money/info')['data']['Trade_Fee']
				    if new_fee != current_fee:
				    	print "##) ALERT: Change in commission fee from %f to %f" % (current_fee, new_fee)
				    	current_fee = new_fee
				    #update derivatives
				    derivatives[4] = derivatives[3]
				    derivatives[3] = derivatives[2]
				    derivatives[2] = derivatives[1]
				    derivatives[1] = derivatives[0]
				    derivatives[0] = price_change
				    print derivatives
                
                #record the data to the spreadsheet
                if update_counter != 0:     
                    writer.writerow([update_counter, current_time, bid_price_print, price_change * price_change_sign, current_fee])
                    
                previous_time = current_time
                previous_price = bid_price_print
                   
        except Exception as e:
                print "Error - %s" % e
                        
        update_counter += 1
        print ""
        
        time.sleep(5)



if __name__ == '__main__':

  print "\n"
  arg_length = len(sys.argv)
  if(arg_length == 1):
    mainloop()
  else:
    if(arg_length == 2):
      if(sys.argv[1] == "margin"):
        margin()
      elif(sys.argv[1] == "status"):
        status_update()
      else:
        print "WARNING: invalid argument %s" % (sys.argv[1])

  print "\n"







