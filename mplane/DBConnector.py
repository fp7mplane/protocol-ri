#!/usr/bin/python
import sqlite3
import json

plugin_filename = './plugin_test.out'

q_create_plugin = ''' CREATE TABLE IF NOT EXISTS plugin (
    sid INT,
    session_start DATETIME,
    probe_id INT,
    http_id INT,
    session_url TEXT,
    host TEXT,
    uri TEXT,
    tab_id INT,
    local_ip TEXT,
    local_port INT,
    remote_ip TEXT,
    remote_port INT,
    request_ts DATETIME,
    get_sent_tst DATETIME,
    syn_start DATETIME,
    syn_time INT,
    data_trans INT,
    dns_start DATETIME,
    dns_time INT,
    end_time DATETIME,
    first_bytes_rcv DATETIME,
    full_load_time DATETIME,
    app_rtt FLOAT,
    get_bytes INT,
    header_bytes INT,
    body_bytes INT,
    content_len INT,
    content_type TEXT,
    response_code INT,
    keep_alive BOOLEAN,
    cpu_percent FLOAT,
    mem_percent FLOAT,
    ping_gateway FLOAT,
    ping_google FLOAT,
    cache INT,
    cache_bytes INT,
    annoy BOOLEAN,
    PRIMARY KEY(sid, probe_id,http_id,request_ts)
    );
    '''

q_create_active = ''' CREATE TABLE IF NOT EXISTS active(
    sid INT8,
    session_url TEXT,
    remote_ip TEXT,
    ping TEXT,
    trace TEXT,
    sent INT,
    PRIMARY KEY(sid, remote_ip)
    );
    ''' 


def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1
    
class DBConnector():
    def __init__(self, dbname):
        self.db = sqlite3.connect(dbname)
        self._check_tables()

    def _check_tables(self):
        queries = [q_create_plugin, q_create_active]
        for q in queries:
            c = self.db.cursor()
            c.execute(q)
        self.db.commit()

    def _insert_dic_to_db(self, tablename, dic):
        query_str = "INSERT INTO %s ({}) VALUES({})" % tablename
        columns, values = zip(*dic.items())
        q = query_str.format(",".join(columns), ",".join("?"*len(values)))
        c = self.db.cursor()
        c.execute(q, values)
        self.db.commit()

    def _execute_query(self, query):
        c = self.db.cursor()
        c.execute(query)
        return c.fetchall()
        
    def _execute_update(self, update):
        c = self.db.cursor()
        c.execute(update)
        self.db.commit()

    def execute_query(self, query):
        return self._execute_query(query)
        
    # TO BE REMOVED as soon as the plugin is updated
    def _translate_dic(self, dic):
        d = {}
        d['sid'] = ''
        d['session_start'] = dic['pageStart']
        d['probe_id'] = dic['ID']
        d['http_id'] = dic['httpid']
        d['session_url'] = dic['pageURL']
        d['host'] = dic['host']
        d['uri'] = dic['uri']
        d['tab_id'] = dic['tabId']
        d['local_ip'] = dic['cIP']
        d['local_port'] = dic['cPort']
        d['remote_ip'] = dic['sIP']
        d['remote_port'] = dic['sPort']
        d['request_ts'] = dic['ts']
        d['get_sent_tst'] = dic['http1']
        d['syn_start'] = dic['tcp1']
        d['syn_time'] = dic['tcp']
        d['data_trans'] = dic['rcv']
        d['dns_start'] = dic['dns1']
        d['dns_time'] = dic['dns']
        d['end_time'] = dic['EndTS']
        d['first_bytes_rcv'] = dic['http2']
        d['full_load_time'] = dic['onLoad']
        d['app_rtt'] = dic['http']
        d['get_bytes'] = dic['GET_Byte']
        d['header_bytes'] = dic['HeaderByte']
        d['body_bytes'] = dic['BodyByte']
        d['content_len'] = dic['len']
        d['content_type'] = dic['type']
        d['response_code'] = dic['status']
        d['keep_alive'] = dic['s_cnxs']
        d['cpu_percent'] = ''
        d['mem_percent'] = ''
        d['ping_gateway'] = dic['pingGW']
        d['ping_google'] = dic['pingG']
        d['cache'] = dic['cache']
        d['cache_bytes'] = dic['CacheByte']
        d['annoy'] = dic['Annoy1st']
        return d

    def _generate_sid(self):
        q = "select distinct session_start from plugin where sid = '';"
        to_update = self._execute_query(q)
        q = "select max(sid) from plugin;"
        res = self._execute_query(q)
        assert len(res) == 1
        if res[0][0] == '':
            max_sid = 1
        else:
            max_sid = int(res[0][0])
        for i in range(len(to_update)):
            q = "update plugin set sid = %d where session_start = '%s';" % (max_sid, to_update[i][0])
            self._execute_update(q)
        
    def load_firelog_file(self, fname):
        #from pprint import pprint
        f = open(fname, 'r')
        lines = f.readlines()
        f.close()
        for line in lines:
            json_data = json.loads( line.strip() )
            data = self._translate_dic(json_data)
            self._insert_dic_to_db('plugin', data)
        self._generate_sid()
            
if __name__ == '__main__':
    dbc = DBConnector('firelog.db')
    dbc.load_firelog_file(plugin_filename)
