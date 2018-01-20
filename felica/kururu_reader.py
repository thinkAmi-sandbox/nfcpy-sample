# -*- coding: utf-8 -*-
# 以下を参考にKURURUを読みました。m2wasabiさん、ありがとうございます。
# https://github.com/m2wasabi/nfcpy-suica-sample/blob/master/suica_read.py
import struct
import textwrap

import nfc
import nfc.tag.tt3

KURURU_SERVICE_CODE = 0x000f


class HistoryRecord(object):
    def __init__(self, data):
        # ビッグエンディアンでバイト列を解釈したもの
        # 1byteで構成するものはB、2byteで構成するものはH、4byteで構成するものはIとなる
        self.row_be = struct.unpack('>HBHBHHBBI', data)
        # リトルエンディアンでバイト列を解釈したもの(くるるの場合は存在せず)
        self.row_le = struct.unpack('<HBHBHHBBI', data)

    def is_empty(self):
        # 年月日がオールゼロの場合、履歴が無い空のレコードとみなす
        return not all([
            self.fetch_year(),
            self.fetch_month(),
            self.fetch_day(),
        ])

    def fetch_year(self):
        # 年: 16bit中、上位7bitを取得すればよい
        # 1. 8bit~16bitは不要なので、9bit右にシフトして捨てる
        #    6988(10進)の場合、bin(6988 >> 9)とすると、 '0b1101' になる
        # 2. 残ったbitと、年の算出で必要な7bitとで論理積を取る
        #    0b1101と0b1111111(16進数だと0x7f)との論理積で、0b1101が残る
        #    -> 結果は、10進int表現の13になる
        return (self.row_be[0] >> 9) & 0b1111111

    def fetch_month(self):
        # 月: 16bit中、先頭から8bit~11bitを取得すればよい
        # 1. 12bit~16bitは不要なので、5bit右にシフトして捨てる
        #    6988(10進)の場合、bin(6988 >> 5)とすると、 '0b11011010' になる
        # 2. 残ったbitのうち、月の算出で必要な下位4bitとで論理積を取る
        #    0b11011010と0b1111(16進数だと0x0f)との論理積で、0b1010が残る
        #    -> 結果は、10進int表現の10になる
        return (self.row_be[0] >> 5) & 0b1111

    def fetch_day(self):
        # 日: 16bit中、下位4bitを取得すればよい
        # 1. 下位4bitなので、不要な桁はない
        #    6988(10進)の場合、bin(6988 >> 0)とすると、 もとの値のまま '0b1101101001100' となる
        #    なので、今回はシフト演算はしない
        # 2. 残ったbitと、日の算出で必要な5bitとで論理積を取る
        #    0b1101101001100と0b11111(16進数だと0x1f)との論理積で、0b1100が残る
        #    -> 結果は、10進int表現の12になる
        return self.row_be[0] & 0b11111

    def fetch_alighting_time(self):
        return self.format_time(self.row_be[1])

    def fetch_machine_no(self):
        return self.row_be[2]

    def fetch_boarding_time(self):
        return self.format_time(self.row_be[3])

    def fetch_boarding_stop(self):
        return self.row_be[4]

    def fetch_alighting_stop(self):
        return self.row_be[5]

    def fetch_place(self):
        # 上位4bitが場所になるので、下位4bitを切り捨て、残りの4bitの論理積を取る
        place = (self.row_be[6] >> 4) & 0b1111
        # 値を見ると、16進のint型なので、16進のintをキーに値を取得する
        # print type(place)  # => int
        # print hex(place)   # => 0xe
        # print place        # => 14
        # 辞書のキーは、Suica版に合わせて16進数表記としておく
        result = {
            0x05: '車内 ({})',
            0x07: '営業所 ({})',
            0x0E: '券売機 ({})',
        }.get(place, '不明 ({})')
        return result.format(hex(place))

    def fetch_category(self):
        # 下位4bitがカテゴリになるので、下位4bitの論理積を取る
        category = self.row_be[6] & 0b1111
        result = {
            0x00: '入金 ({})',
            0x02: '支払 ({})',
        }.get(category, '不明 ({})')
        return result.format(hex(category))

    def fetch_company(self):
        company = (self.row_be[7] >> 4) & 0b1111
        result = {
            0x00: '長電バス ({})',
            0x03: 'アルピコバス ({})',
        }.get(company, '不明 ({})')
        return result.format(hex(company))

    def fetch_discount(self):
        discount = self.row_be[7] & 0b1111
        result = {
            0x00: '入金 ({})',
            0x01: 'なし ({})',
        }.get(discount, '不明 ({})')
        return result.format(hex(discount))

    def fetch_balance(self):
        return self.row_be[8]

    def format_time(self, usage_time):
        # usage_timeは、10進のintに見えるが、実際には16進のint
        # そのため、これを、10進のintにする必要がある

        # 16進のintを16進表現の文字列にする
        hex_time = hex(usage_time)
        # 16進表現の文字列を10進数値にする
        int_time = int(hex_time, 16)
        # 1/10されているので、元に戻す
        origin_time = int_time * 10
        # 商(時間)と余り(分)を取得する
        # 元々は分単位なので、時間単位にする
        hm = divmod(origin_time, 60)
        return '{hm[0]:02d}:{hm[1]:02d}:00'.format(hm=hm)


def connected(tag):

    # ServiceCodeクラスのコンストラクタの引数について
    # ・第一引数は、サービス番号 (サービスコードの上位10bit)
    #   不要な下位6bitは捨てる
    # ・第二引数は、属性値 (サービスコードの下位6bit)
    #   2進数111111を16進数で表すと、3f (下位6bitの取り出しを論理積にしてるので、その部分が出てくる)
    sc = nfc.tag.tt3.ServiceCode(KURURU_SERVICE_CODE >> 6, KURURU_SERVICE_CODE & 0x3f)
    for i in range(0, 10):
        bc = nfc.tag.tt3.BlockCode(i, service=0)
        data = tag.read_without_encryption([sc], [bc, ])

        history = HistoryRecord(bytes(data))
        if history.is_empty():
            continue

        result = """
        Block: {history_no}
        日付: {yyyy}/{mm}/{dd}
        機番: {machine}
        乗車時刻: {boarding_time}
        乗車停留所: {boarding_stop}
        降車時刻: {alighting_time}
        降車停留所: {alighting_stop}
        場所: {place}
        種別: {category}
        会社: {company}
        割引: {discount}
        残高: {balance:,}円
        """.format(
            history_no=i + 1,
            yyyy=history.fetch_year() + 2000,
            mm='{:02d}'.format(history.fetch_month()),
            dd='{:02d}'.format(history.fetch_day()),
            machine=history.fetch_machine_no(),
            boarding_time=history.fetch_boarding_time(),
            boarding_stop=history.fetch_boarding_stop(),
            alighting_time=history.fetch_alighting_time(),
            alighting_stop=history.fetch_alighting_stop(),
            place=history.fetch_place(),
            category=history.fetch_category(),
            company=history.fetch_company(),
            discount=history.fetch_discount(),
            balance=history.fetch_balance(),
        )
        print '-' * 30
        print textwrap.dedent(result)


def main():
    with nfc.ContactlessFrontend('usb') as clf:
        clf.connect(rdwr={'on-connect': connected})


if __name__ == '__main__':
    # 参考
    # https://stackoverflow.com/questions/2611858/struct-error-unpack-requires-a-string-argument-of-length-4/2612851
    f = struct.calcsize('=HBHBHHBBHH')
    print 'フォーマットの桁数：{}'.format(f)

    main()
