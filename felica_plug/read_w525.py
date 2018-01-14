# -*- coding: utf-8 -*-
# https://nfcpy.readthedocs.io/en/latest/topics/get-started.html#read-and-write-tags
import nfc
import nfc.tag.tt3
import binascii


def connected(tag):
    print tag
    # => Type3Tag 'FeliCa Plug (RC-S926)' ID=03xxxxxxxxxxxxxx PMM=01xxxxxxxxxxxxxx SYS=FEE1

    print type(tag)
    # => <class 'nfc.tag.tt3_sony.FelicaPlug'>

    print dir(tag)
    # =>
    # ['IC_CODE_MAP', 'NDEF', 'TYPE', '__class__', '__delattr__', '__dict__', '__doc__',
    #  '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__',
    #  '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
    #  '__subclasshook__', '__weakref__', '_authenticated', '_clf', '_format', '_is_present',
    #  '_ndef', '_nfcid', '_product', '_target', 'authenticate', 'clf', 'dump', 'dump_service',
    #  'format', 'identifier', 'idm', 'is_authenticated', 'is_present', 'ndef', 'pmm', 'polling',
    #  'product', 'protect', 'read_from_ndef_service', 'read_without_encryption',
    #  'send_cmd_recv_rsp', 'sys', 'target', 'type', 'write_to_ndef_service',
    #  'write_without_encryption']

    print tag.polling(tag.sys)
    # => (bytearray(b'\x03\xxx\xxx\xxx\xxx\xxx\xxx\xxx'),
    #     bytearray(b'\x01\xxx\xxx\xxx\xxx\xxx\xxx\xxx'))

    sc = nfc.tag.tt3.ServiceCode(0, 0x0b)
    bc1 = nfc.tag.tt3.BlockCode(0, service=0)
    bc2 = nfc.tag.tt3.BlockCode(1, service=0)
    data = tag.read_without_encryption([sc], [bc1, bc2])
    print '{}'.format(binascii.hexlify(data))
    # => 02fd8c73947acef9742874c2b8429cc1d7dab10accf72bd5318863f862dc0371

    print tag.dump()
    # => ['This is not an NFC Forum Tag.']

    print tag.dump_service(sc)
    # =>
    # ['0000: 02 fd 8c 73 94 7a ce f9 74 28 74 c2 b8 42 9c c1 |...s.z..t(t..B..|',
    #  '*     02 fd 8c 73 94 7a ce f9 74 28 74 c2 b8 42 9c c1 |...s.z..t(t..B..|',
    #  '6962: 02 fd 8c 73 94 7a ce f9 74 28 74 c2 b8 42 9c c1 |...s.z..t(t..B..|']


def main():
    with nfc.ContactlessFrontend('usb') as clf:
        clf.connect(rdwr={'on-connect': connected})


if __name__ == '__main__':
    main()
