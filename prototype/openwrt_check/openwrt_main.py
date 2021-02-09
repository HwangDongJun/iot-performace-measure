from scapy.all import *
from scapy.layers.dns import DNS, DNSQR
from datetime import datetime
import subprocess
import threading
import os
import time
import pandas as pd
import pickle


class openwrt_class(object):
    def __init__(self, name, ip_addr):
        self.name = name
        self.ip_addr = ip_addr

    def inspect_packet(self, get_rental_equipment=False):
        if get_rental_equipment:
            self.get_rental_equipment_file()

        mac_name = dict()
        with open('./rental_equipment_status/dhcp.leases', 'r') as fr:
            lines = fr.readlines()
            for line in lines:
                line_split = line.split(' ')
                mac_name[line_split[1]] = line_split[3]
        dns_packets = rdpcap('./packet_file/dns_packet.pcap')
        host_list = list(); page_list = list(); time_list = list()
        for packet in dns_packets:
            if packet[DNS] and packet[Ether].src in list(mac_name.keys()):
                host_list.append(mac_name[packet[Ether].src])
                page_list.append(packet[DNS].qd.qname.decode())
                time_list.append(datetime.utcfromtimestamp(int(packet.time) + 32400))
        #print({'User' : host_list, 'Link' : page_list, 'Date' : time_list})
        capture_df = pd.DataFrame({'User' : host_list, 'Link' : page_list, 'Date' : time_list})
        # capture_df.to_csv('./capture_csv_file/' + str(time_list[-1]))
        return capture_df

    def check_blacklist(self):
        res = ''
        blacklist = list()

        # blacklist
        with open('./blacklist.pickle', 'rb') as fr:
            blacklist = pickle.load(fr)

        subprocess.call('ssh {}@{} "iptables -A FORWARD -m string --string \"{}\" --algo kmp -j DROP"'.format(self.name, self.ip_addr, 'naver'), shell=True)
        #for bl in blacklist:
        #    try:
        #        subprocess.call('ssh {}@{} "iptables -A FORWARD -p tcp --dport 80 -m string --string \"Host: {}\" --algo kmp -j DROP" 2>&1'.format(self.name, self.ip_addr, bl), shell=True)
        #    except:
        #        continue

        # inspect_packet이랑 해당 함수 같이해서 blacklist 확인해서 차단할 방법 구현
        # 1단계 가장 간단하게 이름이 같은 URL이 겹칠경우 차단
        # get_user_link_capture = self.inspect_packet()
        # for gulc in list(get_user_link_capture['Link'].values):
        #     catch_url = ''
        #     if gulc in blacklist:
        #         if 'http' in gulc:
        #             catch_url = gulc[7:]

        #             if catch_url[-1] == '/':
        #                 catch_url = catch_url[:-1]

                    # iptables를 통해 사이트 차단 (확실한 검증 필요.) [추가: https의 경우 차단하지 못함]
        #             subprocess.call('ssh {}@{} "iptables -A FORWARD -p tcp --dport 80 -m string --string \"Host: {}\" --algo kmp -j DROP"'.format(self.name, self.ip_addr, catch_url), shell=True)
        #             #time.sleep(1)

        '''
        1. 키워드로 필터링
            iptables -A FORWARD -p tcp --dport 80 -m string --string "naver" --algo bm -j DROP

        2. URL로 필터링
            iptables -A FORWARD -p tcp --dport 80 -m string --string "Host: www.naver.com" --algo bm -j DROP
        '''

        #             res = '1' # 상황 1번 : 정상 차단 성공
        #         elif 'https' in gulc:
        #             res = '2' # 상황 2번 : https 사이트

        # return res

    def capture_packet(self):
        subprocess.call('ssh {}@{} "tcpdump -c 30 -e -i wlan0 -tttt -s 0 -w - -U udp port 53" > ./packet_file/dns_packet.pcap'.format(self.name, self.ip_addr), shell=True)
        time.sleep(1)
        
    def get_rental_equipment_file(self):
        subprocess.call('scp -r {}@{}:/tmp/dhcp.leases ./rental_equipment_status/'.format(self.name, self.ip_addr), shell=True)
        name_mac_address = dict()
        with open('./rental_equipment_status/dhcp.leases', 'r') as fr:
            lines = fr.readlines()
            for line in lines:
                router_list = line.split(' ')
                name_mac_address[router_list[1]] = router_list[3]

        return name_mac_address

if __name__ == '__main__':
    start_time = time.time()
    ow_class = openwrt_class("root", "192.168.1.1")

    # ow_class.get_rental_equipment_file()
    #ow_class.capture_packet()
    ow_class.check_blacklist()
    print(time.time() - start_time)