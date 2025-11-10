#-*- coding:utf-8 -*-    
#--------------Ashare 股票行情数据双核心版( https://github.com/mpquant/Ashare ) 
import json,requests,datetime,time;      import pandas as pd  #

#腾讯日线
def get_price_day_tx(code, end_date='', count=10, frequency='1d'):     #日线获取  
    unit='week' if frequency in '1w' else 'month' if frequency in '1M' else 'day'     #判断日线，周线，月线
    if end_date:  end_date=end_date.strftime('%Y-%m-%d') if isinstance(end_date,datetime.date) else end_date.split(' ')[0]
    end_date='' if end_date==datetime.datetime.now().strftime('%Y-%m-%d') else end_date   #如果日期今天就变成空    
    URL=f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{unit},,{end_date},{count},qfq'     
    st= json.loads(requests.get(URL).content);    ms='qfq'+unit;      stk=st['data'][code]   
    buf=stk[ms] if ms in stk else stk[unit]       #指数返回不是qfqday,是day
    df=pd.DataFrame(buf,columns=['time','open','close','high','low','volume'],dtype='float')     
    df.time=pd.to_datetime(df.time);    df.set_index(['time'], inplace=True);   df.index.name=''          #处理索引 
    return df

#腾讯分钟线
def get_price_min_tx(code, end_date=None, count=10, frequency='1d'):    #分钟线获取 
    ts=int(frequency[:-1]) if frequency[:-1].isdigit() else 1           #解析K线周期数
    if end_date: end_date=end_date.strftime('%Y-%m-%d') if isinstance(end_date,datetime.date) else end_date.split(' ')[0]        
    URL=f'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m{ts},,{count}' 
    st= json.loads(requests.get(URL).content);       buf=st['data'][code]['m'+str(ts)] 
    df=pd.DataFrame(buf,columns=['time','open','close','high','low','volume','n1','n2'])   
    df=df[['time','open','close','high','low','volume']]    
    df[['open','close','high','low','volume']]=df[['open','close','high','low','volume']].astype('float')
    df.time=pd.to_datetime(df.time);   df.set_index(['time'], inplace=True);   df.index.name=''          #处理索引     
    df['close'][-1]=float(st['data'][code]['qt'][code][3])                #最新基金数据是3位的
    return df


#sina新浪全周期获取函数，分钟线 5m,15m,30m,60m  日线1d=240m   周线1w=1200m  1月=7200m
def get_price_sina(code, end_date='', count=10, frequency='60m'):    #新浪全周期获取函数    
    frequency=frequency.replace('1d','240m').replace('1w','1200m').replace('1M','7200m');   mcount=count
    ts=int(frequency[:-1]) if frequency[:-1].isdigit() else 1       #解析K线周期数
    if (end_date!='') & (frequency in ['240m','1200m','7200m']): 
        end_date=pd.to_datetime(end_date) if not isinstance(end_date,datetime.date) else end_date    #转换成datetime
        unit=4 if frequency=='1200m' else 29 if frequency=='7200m' else 1    #4,29多几个数据不影响速度
        count=count+(datetime.datetime.now()-end_date).days//unit            #结束时间到今天有多少天自然日(肯定 >交易日)        
        #print(code,end_date,count)    
    URL=f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale={ts}&ma=5&datalen={count}' 
    dstr= json.loads(requests.get(URL).content);       
    #df=pd.DataFrame(dstr,columns=['day','open','high','low','close','volume'],dtype='float') 
    df= pd.DataFrame(dstr,columns=['day','open','high','low','close','volume'])
    df['open'] = df['open'].astype(float); df['high'] = df['high'].astype(float);                          #转换数据类型
    df['low'] = df['low'].astype(float);   df['close'] = df['close'].astype(float);  df['volume'] = df['volume'].astype(float)    
    df.day=pd.to_datetime(df.day);    df.set_index(['day'], inplace=True);     df.index.name=''            #处理索引                 
    if (end_date!='') & (frequency in ['240m','1200m','7200m']): return df[df.index<=end_date][-mcount:]   #日线带结束时间先返回              
    return df

def get_price(code, end_date='',count=10, frequency='1d', fields=[]):        #对外暴露只有唯一函数，这样对用户才是最友好的  
    xcode= code.replace('.XSHG','').replace('.XSHE','')                      #证券代码编码兼容处理 
    xcode='sh'+xcode if ('XSHG' in code)  else  'sz'+xcode  if ('XSHE' in code)  else code     

    if  frequency in ['1d','1w','1M']:   #1d日线  1w周线  1M月线
         try:    return get_price_sina( xcode, end_date=end_date,count=count,frequency=frequency)   #主力
         except: return get_price_day_tx(xcode,end_date=end_date,count=count,frequency=frequency)   #备用                    
    
    if  frequency in ['1m','5m','15m','30m','60m']:  #分钟线 ,1m只有腾讯接口  5分钟5m   60分钟60m
         if frequency in '1m': return get_price_min_tx(xcode,end_date=end_date,count=count,frequency=frequency)
         try:    return get_price_sina(  xcode,end_date=end_date,count=count,frequency=frequency)   #主力   
         except: return get_price_min_tx(xcode,end_date=end_date,count=count,frequency=frequency)   #备用


def get_realtime_quotes_sina(stock_codes):
    """
    获取实时行情数据（新浪接口）
    
    参数：
        stock_codes: 股票代码列表或单个代码
                    支持格式：['sh000001', 'sz000001'] 或 'sh000001,sz000001'
    
    返回：
        dict: {code: {name, price, open, high, low, ...}}
    """
    # 统一处理为列表
    if isinstance(stock_codes, str):
        if ',' in stock_codes:
            codes_list = stock_codes.split(',')
        else:
            codes_list = [stock_codes]
    else:
        codes_list = stock_codes
    
    # 格式化代码
    formatted_codes = []
    for code in codes_list:
        xcode = code.replace('.XSHG', '').replace('.XSHE', '')
        
        # 如果已经有前缀，直接使用
        if xcode.startswith('sh') or xcode.startswith('sz'):
            formatted_codes.append(xcode)
        # 如果是聚宽格式，转换
        elif 'XSHG' in code:
            formatted_codes.append('sh' + xcode)
        elif 'XSHE' in code:
            formatted_codes.append('sz' + xcode)
        # 纯数字，根据规则判断市场
        elif xcode.isdigit():
            if xcode.startswith('6'):
                formatted_codes.append('sh' + xcode)  # 60开头是上海主板
            elif xcode.startswith('0') or xcode.startswith('3'):
                formatted_codes.append('sz' + xcode)  # 00开头是深圳主板，30开头是创业板
            else:
                formatted_codes.append(xcode)  # 其他情况保持原样
        else:
            formatted_codes.append(xcode)  # 其他情况保持原样
    
    # 构建请求
    timestamp = int(time.time() * 1000)
    codes_str = ','.join(formatted_codes)
    url = f'https://hq.sinajs.cn/rn={timestamp}&list={codes_str}'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}
        
        # 解析数据
        result = {}
        lines = response.text.strip().split('\n')
        
        for line in lines:
            if 'hq_str_' in line and '="' in line:
                parts = line.split('="')
                if len(parts) >= 2:
                    code = parts[0].split('hq_str_')[1]
                    data = parts[1].rstrip('";')
                    fields = data.split(',')
                    
                    if len(fields) >= 32 and fields[0]:  # 确保有数据
                        try:
                            current_price = float(fields[3])
                            open_price = float(fields[1])
                            prev_close = float(fields[2])
                            
                            result[code] = {
                                'name': fields[0],
                                'current_price': current_price,
                                'open': open_price,
                                'prev_close': prev_close,
                                'high': float(fields[4]),
                                'low': float(fields[5]),
                                'volume': float(fields[8]),
                                'amount': float(fields[9]),
                                'change': current_price - prev_close,
                                'change_pct': ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0,
                                'time': f"{fields[30]} {fields[31]}"
                            }
                        except (ValueError, IndexError):
                            continue
        
        return result
        
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return {}


def get_stock_name(stock_code):
    """
    获取股票名称
    
    参数：
        stock_code: 股票代码，支持多种格式
                   - 纯数字：000001, 600519
                   - 带前缀：sh000001, sz000001
                   - 聚宽格式：000001.XSHG, 600519.XSHG
    
    返回：
        str: 股票名称，失败返回None
    """
    # 格式化代码
    xcode = stock_code.replace('.XSHG', '').replace('.XSHE', '')
    
    # 如果已经有前缀，直接使用
    if xcode.startswith('sh') or xcode.startswith('sz'):
        pass
    # 如果是聚宽格式，转换
    elif 'XSHG' in stock_code:
        xcode = 'sh' + xcode
    elif 'XSHE' in stock_code:
        xcode = 'sz' + xcode
    # 纯数字，根据规则判断市场
    elif xcode.isdigit():
        if xcode.startswith('6'):
            xcode = 'sh' + xcode  # 60开头是上海主板
        elif xcode.startswith('0') or xcode.startswith('3'):
            xcode = 'sz' + xcode  # 00开头是深圳主板，30开头是创业板
        else:
            # 尝试两个市场
            for prefix in ['sh', 'sz']:
                test_code = prefix + xcode
                quotes = get_realtime_quotes_sina(test_code)
                if test_code in quotes:
                    return quotes[test_code]['name']
            return None
    
    quotes = get_realtime_quotes_sina(xcode)
    
    if xcode in quotes:
        return quotes[xcode]['name']
    return None


def get_intraday_data(stock_code, count=240):
    """
    获取今日分时数据（1分钟线）
    
    参数：
        stock_code: 股票代码，支持多种格式
        count: 获取数据条数，默认240（一个交易日约240分钟）
    
    返回：
        DataFrame: 包含时间、开高低收、成交量
    """
    try:
        # 格式化代码
        xcode = stock_code.replace('.XSHG', '').replace('.XSHE', '')
        
        # 如果已经有前缀，直接使用
        if xcode.startswith('sh') or xcode.startswith('sz'):
            pass
        # 如果是聚宽格式，转换
        elif 'XSHG' in stock_code:
            xcode = 'sh' + xcode
        elif 'XSHE' in stock_code:
            xcode = 'sz' + xcode
        # 纯数字，根据规则判断市场
        elif xcode.isdigit():
            if xcode.startswith('6'):
                xcode = 'sh' + xcode
            elif xcode.startswith('0') or xcode.startswith('3'):
                xcode = 'sz' + xcode
        
        # 获取1分钟数据
        df = get_price(xcode, frequency='1m', count=count)
        
        if df.empty:
            return None
        
        # 重置索引，将时间作为列
        df = df.reset_index()
        df.columns = ['time', 'open', 'close', 'high', 'low', 'volume']
        
        return df
        
    except Exception as e:
        print(f"获取分时数据失败: {e}")
        return None

        
if __name__ == '__main__':
    df=get_price('sh000001',frequency='1d',count=10)      #支持'1d'日, '1w'周, '1M'月  
    print('上证指数日线行情\n',df)
    
    df=get_price('000001.XSHG',frequency='15m',count=10)  #支持'1m','5m','15m','30m','60m'
    print('上证指数分钟线\n',df)

# Ashare 股票行情数据( https://github.com/mpquant/Ashare )