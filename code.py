#  SPDX-FileCopyrightText: 2021 Jeff Epler for Adafruit Industries
# 
#  SPDX-License-Identifier: MIT

import keypad
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard, find_device
from adafruit_hid.keycode import Keycode

key_pins = [
    board.GP2,# 1P 0,1,は皿  2,3,4,5,6,7,8は鍵盤
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
    board.GP13,# 2P 13,14,15,18,19,20,21が鍵盤
    board.GP14,
    board.GP15,# GP16、17は皿
    board.GP18,
    board.GP19,
    board.GP20,
    board.GP21,
    board.GP22,
    board.GP26,
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

        #  report[0] modifiers
        #  report[1:16] regular key presses bitmask
        self.report = bytearray(16)

        self.report_modifier = memoryview(self.report)[0:1]
        self.report_bitmap = memoryview(self.report)[1:]

    def _add_keycode_to_report(self, keycode):
        modifier = Keycode.modifier_bit(keycode)
        if modifier:
            #  Set bit for this modifier.
            self.report_modifier[0] |= modifier
        else:
            self.report_bitmap[keycode >> 3] |= 1 << (keycode & 0x7)

    def _remove_keycode_from_report(self, keycode):
        modifier = Keycode.modifier_bit(keycode)
        if modifier:
            #  Set bit for this modifier.
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

# キーコード https://docs.circuitpython.org/projects/hid/en/4.1.6/api.html
keyCodes = [Keycode.Q,Keycode.W,Keycode.E,Keycode.R,Keycode.T,Keycode.Y,Keycode.U,Keycode.ENTER,Keycode.BACKSPACE,Keycode.P,Keycode.L,Keycode.K,Keycode.J,
             Keycode.H,Keycode.G,Keycode.F,Keycode.D,Keycode.S,Keycode.A,Keycode.Z,Keycode.ENTER,Keycode.BACKSPACE,Keycode.X,Keycode.C,Keycode.C,Keycode.C]
scrUp = [Keycode.LEFT_SHIFT,Keycode.M]
scrDown = [Keycode.CONTROL,Keycode.N]
kbd = BitmapKeyboard(usb_hid.devices)

# 除数
DIVISOR = 1
encoder = [rotaryio.IncrementalEncoder(GP0,GP1,DIVISOR),rotaryio.IncrementalEncoder(GP16,GP17,DIVISOR)]
# 前フレームの位置(変化確認用)
prePos = [0,0]

# 皿が反応するまでにどのくらい回すかを設定する為の数値
COUNT_MAX = 4
# 以下がCOUNT_MAXを超えたら皿が反応する
count = [0,0]
preCount = [0,0]

# 回したらどのくらい反応させたままにするか
REACTION_COUNT_MAX = 1500
# 以下がREACTION_COUNT_MAXを超えたら皿の反応がなくなる
reactionCount = [0,0]

# 回転フラグ
upRot = [0,0]
downRot = [0,0]
finalRotUp = [0,0]

# 一旦止めないと再入力できないようにするための変数
rotAfterTheEndStop = [1,1]

# 短時間で同一方向に入力できないようにする変数
# 入力後に以下の変数の加算が開始し、notCountChangeTime == NOT_COUNT_CHANGE_TIME_MAXになったら同じ方向への入力が可能になる
notCountChangeTime = [0,0]
NOT_COUNT_CHANGE_TIME_MAX = 3500
    

# IIDXモード
# アーケード版IIDXを再現

# EZ2ONモード
# コントローラーをEZ2ONで使えるようにするモード
# 皿を回してすぐに反対側に回したら数msだけ皿の反応を無くし、連続入力を可能にする
# EZ2ONは片方のキー、ボタンを押している間にもう片方のキー、ボタンを押しても反応しない(このコントローラーを使う場合はキー、ボタン = 皿で、皿を回している間に反対側に回しても反応しない)ので、上記の処理が必要
    
MODE_IIDX = 0
MODE_EZ2ON = 1
MODE_MAX = MODE_EZ2ON
currentMode = MODE_IIDX
prePushModeButton = 0
modeChangeButton = digitalio.DigitalInOut(GP27)
modeChangeButton.direction = digitalio.Direction.INPUT
modeChangeButton.pull = digitalio.Pull.UP

def changeMode():
    # 押された瞬間モード切替
        if modeChangeButton == True and prePushModeButton == 0:
            currentMode = currentMode + 1
            prePushModeButton = 1
            if currentMode == MODE_MAX:
                currentMode = 0
        else:
            prePushModeButton = 0
            
    
# プレイヤー番号は0スタート
# ここわざわざ引数にしなくてもいいかも
def checkButton():
    ev = keys.events.get()
    if ev is not None:
        key = keyCodes[ev.key_number]
        if ev.pressed:
            kbd.press(key)
        else:
            kbd.release(key)

 

def checkEncoder(playerNum):
    global prePos,preCount,count,reactionCount,upRot,downRot,finalRotUp,rotAfterTheEndStop,stopAfterTheEndRot,notCountChangeTime
    pos = encoder[playerNum].position
    cPos = pos - prePos[playerNum]
    moveDir = 0# 1下 -1上 0未回転 
    if cPos > 0:
        moveDir = 1
    elif cPos < 0:
        moveDir = -1
    else:
        moveDir = 0
          
    # 上回転
    if moveDir == -1: 
        if count[playerNum] > 0:# プラスだったら0を代入
            count[playerNum] = 0
        count[playerNum] = count[playerNum] - 1
        if count[playerNum] < -COUNT_MAX:
            reactionCount[playerNum] = 0# 回したら反応時間をリセット
        
        #if count[playerNum] < -COUNT_MAX and rotAfterTheEndStop[playerNum] == 1 or finalRotUp[playerNum] == 0 and count[playerNum] < -COUNT_MAX:# 条件満たしたら入力
        if count[playerNum] < -COUNT_MAX or finalRotUp[playerNum] == 0 and count[playerNum] < -COUNT_MAX:# 条件満たしたら入力
            downRot[playerNum] = 0 # 逆に回転していたら中止
            kbd.press(scrUp[playerNum])
            kbd.release(scrDown[playerNum])
            upRot[playerNum] = 1
            count[playerNum] = 0
            finalRotUp[playerNum] = 1
            rotAfterTheEndStop[playerNum] = 0
            notCountChangeTime[playerNum] = 0
    # 下回転
    elif moveDir == 1:
        if count[playerNum] < 0:# マイナスだったら0を代入
            count[playerNum] = 0
        count[playerNum] = count[playerNum] + 1
        if count[playerNum] > COUNT_MAX:
            reactionCount[playerNum] = 0# 回したら反応時間をリセット
            
        if count[playerNum] > COUNT_MAX and rotAfterTheEndStop[playerNum] == 1 or finalRotUp[playerNum] == 1 and count[playerNum] > COUNT_MAX:
            upRot[playerNum] = 0 # 逆に回転していたら中止
            kbd.press(scrDown[playerNum])
            kbd.release(scrUp[playerNum])
            downRot[playerNum] = 1
            count[playerNum] = 0
            finalRotUp[playerNum] = 0
            rotAfterTheEndStop[playerNum] = 0
            notCountChangeTime[playerNum] = 0
    
    prePos[playerNum] = pos
    
    if preCount[playerNum] == count[playerNum]:
        if notCountChangeTime[playerNum] == NOT_COUNT_CHANGE_TIME_MAX:
            notCountChangeTime[playerNum] = NOT_COUNT_CHANGE_TIME_MAX# ここはMAX代入で合ってます
            rotAfterTheEndStop[playerNum] = 1
        else:
            notCountChangeTime[playerNum] = notCountChangeTime[playerNum] + 1
            
    preCount[playerNum] = count
     
    # 回転時間加算と回転入力終了処理
    if upRot[playerNum] == 1:
        reactionCount[playerNum] = reactionCount[playerNum] + 1
        if reactionCount[playerNum] == REACTION_COUNT_MAX:# 一定時間経ったら回転中止
            reactionCount[playerNum] = 0
            upRot[playerNum] = 0
            count[playerNum] = 0
            kbd.release(scrUp[playerNum])
            
    elif downRot[playerNum] == 1:
        reactionCount[playerNum] = reactionCount[playerNum]  + 1
        if reactionCount[playerNum] == REACTION_COUNT_MAX:# 一定時間経ったら回転中止
            reactionCount[playerNum] = 0
            downRot[playerNum] = 0
            count[playerNum] = 0
            kbd.release(scrDown[playerNum])
            
        
while True:
    # ボタン処理
     checkButton()
    
    # 1P皿処理
     checkEncoder(0)
     
     # 2P皿処理
     checkEncoder(1)
     
     # モードの切替
     changeMode()

