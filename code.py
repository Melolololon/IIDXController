# SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import keypad
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard, find_device
from adafruit_hid.keycode import Keycode

key_pins = [
    board.GP2,
    board.GP3,
    board.GP4,
    board.GP5,
    board.GP6,
    board.GP7,
    board.GP8,
    board.GP9,
    board.GP10,
    board.GP11,
    board.GP12,
]

keys = keypad.Keys(key_pins, value_when_pressed=False, pull=True)

class BitmapKeyboard(Keyboard):
    def __init__(self, devices):
        device = find_device(devices, usage_page=0x1, usage=0x6)

        try:
            device.send_report(b'\0' * 16)
        except ValueError:
            print("found keyboard, but it did not accept a 16-byte report. check that boot.py is installed properly")

        self._keyboard_device = device

        # report[0] modifiers
        # report[1:16] regular key presses bitmask
        self.report = bytearray(16)

        self.report_modifier = memoryview(self.report)[0:1]
        self.report_bitmap = memoryview(self.report)[1:]

    def _add_keycode_to_report(self, keycode):
        modifier = Keycode.modifier_bit(keycode)
        if modifier:
            # Set bit for this modifier.
            self.report_modifier[0] |= modifier
        else:
            self.report_bitmap[keycode >> 3] |= 1 << (keycode & 0x7)

    def _remove_keycode_from_report(self, keycode):
        modifier = Keycode.modifier_bit(keycode)
        if modifier:
            # Set bit for this modifier.
            self.report_modifier[0] &= ~modifier
        else:
            self.report_bitmap[keycode >> 3] &= ~(1 << (keycode & 0x7))
        
    def release_all(self):
        for i in range(len(self.report)):
            self.report[i] = 0
        self._keyboard_device.send_report(self.report)

 


from board import *
import rotaryio
import usb_hid
import digitalio
import board
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard import Keycode

 

#キーコード https://docs.circuitpython.org/projects/hid/en/4.1.6/api.html
keys1P = [Keycode.Q,Keycode.W,Keycode.E,Keycode.R,Keycode.T,Keycode.Y,Keycode.U,Keycode.ENTER,Keycode.BACKSPACE,Keycode.P,Keycode.L,Keycode.K,Keycode.J]
scrUp1P = Keycode.LEFT_SHIFT
scrDown1P = Keycode.CONTROL
kbd = BitmapKeyboard(usb_hid.devices)


encoder = rotaryio.IncrementalEncoder(GP0,GP1,1)
prePos = 0

#皿が反応するまでにどのくらい回すかを設定する為の数値
countMax = 4
#以下がcountMaxを超えたら皿が反応する
count = 0
preCount = 0

#回したらどのくらい反応させたままにするか
reactionCountMax = 1500
#以下がreactionCountMaxを超えたら皿の反応がなくなる
reactionCount = 0

#回転フラグ
upRot = 0
downRot = 0
finalRotUp = 0

#一旦止めないと再入力できないようにするための変数
rotAfterTheEndStop = 1

#短時間で同一方向に入力できないようにする変数
#入力後に以下の変数の加算が開始し、notCountChangeTime == notCountChangeTimeMaxになったら同じ方向への入力が可能になる
notCountChangeTime = 0
notCountChangeTimeMax = 3500
    
def checkButton():
    ev = keys.events.get()
    if ev is not None:
        key = keys1P[ev.key_number]
        if ev.pressed:
            kbd.press(key)
        else:
            kbd.release(key)

 

def checkEncoder():
    global prePos,preCount,count,reactionCount,upRot,downRot,continuousRotCount,finalRotUp,rotAfterTheEndStop,stopAfterTheEndRot,notCountChangeTime
    pos = encoder.position
    cPos = pos - prePos
    moveDir = 0#1下 -1上 0未回転 
    if cPos > 0:
        moveDir = 1
    elif cPos < 0:
        moveDir = -1
    else:
        moveDir = 0
          
    #上回転
    if moveDir == -1: 
        if count > 0:#プラスだったら0を代入
            count = 0
        count = count - 1
        if count < -countMax:
            reactionCount = 0#回したら反応時間をリセット
        
        if count < -countMax and rotAfterTheEndStop == 1 and finalRotUp == 1 or finalRotUp == 0 and count < -countMax:#条件満たしたら入力
            downRot = 0 #逆に回転していたら中止
            kbd.press(scrUp1P)
            kbd.release(scrDown1P)
            upRot = 1
            count = 0
            finalRotUp = 1
            rotAfterTheEndStop = 0
            notCountChangeTime = 0
    #下回転
    elif moveDir == 1:
        if count < 0:#マイナスだったら0を代入
            count = 0
        count = count + 1
        if count > countMax:
            reactionCount = 0#回したら反応時間をリセット
            
        if count > countMax and rotAfterTheEndStop == 1 and finalRotUp == 0 or finalRotUp == 1 and count > countMax:
            upRot = 0 #逆に回転していたら中止
            kbd.press(scrDown1P)
            kbd.release(scrUp1P)
            downRot = 1
            count = 0
            finalRotUp = 0
            rotAfterTheEndStop = 0
            notCountChangeTime = 0
            reactionCount = 0#回したら反応時間をリセット
    
    prePos = pos
    
    if preCount == count:
        notCountChangeTime = notCountChangeTime + 1
        if notCountChangeTime == notCountChangeTimeMax:
            notCountChangeTime = notCountChangeTimeMax
            rotAfterTheEndStop = 1
            count = 0
            
    preCount = count
     
    #回転時間加算と回転入力終了処理
    if upRot == 1:
        reactionCount = reactionCount + 1
        if reactionCount == reactionCountMax:#一定時間経ったら回転中止
            reactionCount = 0
            upRot = 0
            count = 0
            kbd.release(scrUp1P)
            continuousRotCount = 0
            
    elif downRot == 1:
        reactionCount = reactionCount + 1
        if reactionCount == reactionCountMax:#一定時間経ったら回転中止
            reactionCount = 0
            downRot = 0
            count = 0
            kbd.release(scrDown1P)
            continuousRotCount = 0
            
        
while True:
    #2Pの処理を書く際は、キー以外の変数を配列にし、引数で配列番号を指定して処理すること
     checkEncoder()
     checkButton()
