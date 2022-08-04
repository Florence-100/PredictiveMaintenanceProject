# -*- coding: utf-8 -*-
"""
Created on Thu Feb  3 17:11:45 2022

@author: NG ZHI QING
"""

import time
from collections import deque
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys

#graph variables
currentRUL = 0
currentCummulativeReward = 0
isMaintenance = 0
timeCounter = 0
rulData = deque([currentRUL])
rewardData = deque([currentCummulativeReward])
timeData = deque([timeCounter])
maintenanceData = deque([isMaintenance])

#mqtt topics 
rulValueTopic = ""
rewardTopic = ""
maintenanceActionTopic = ""

#constants
maintenance = 'a1'
noMaintenance = 'a0'

#set up graphs 
fig, (ax1, ax2, ax3) = plt.subplots(3, sharex = True)
    
ax1.set_title('Predicted RUL Value')
ax2.set_title('Maintenance')
ax3.set_title('Cumulative Rewards')
    
line1, = ax1.plot(timeData, rulData, c='blue')
line2, = ax2.plot(timeData, maintenanceData, c='g')
line3, = ax3.plot(timeData, rewardData, c='red')

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected OK')
    else:
        print('Bad connection Returned code = ' + str(rc))

def on_disconnect(client, userdata, flags, rc=0):
    print('Disconnected result code: ' + str(rc))
    
def on_message(client, userdata, message):
    topic = message.topic
    #check if in maintenance 
    global currentCummulativeReward, currentRUL, isMaintenance, timeCounter 
    if topic == rulValueTopic:
        currentRULValue = message.payload.decode("utf-8")
        currentRUL = float(currentRULValue)
        print(f"Current RUL is {currentRUL} at {timeCounter}")
    elif topic == rewardTopic:
        currentReward = message.payload.decode("utf-8")
        currentCummulativeReward += int(currentReward)
        timeCounter += 1
        print(f"Current cumulative reward is {currentCummulativeReward} at {timeCounter}")
    elif topic == maintenanceActionTopic:
        currentAction = message.payload.decode("utf-8")
        if currentAction == maintenance:
            isMaintenance = 1
        else:
            isMaintenance = 0

def animate(i):

    global currentCummulativeReward, currentRUL, timeCounter, isMaintenance, rulData, rewardData, timeData, maintenanceData
    
    timeData.append(timeCounter)
    rulData.append(currentRUL)
    rewardData.append(currentCummulativeReward)
    maintenanceData.append(isMaintenance)

    ax1.relim()
    ax1.autoscale_view()
    ax2.set_ylim(bottom=-0.01, top=1.01)
    ax2.autoscale_view()
    ax3.relim()
    ax3.autoscale_view()
    
    line1.set_data(timeData, rulData)
    line2.set_data(timeData, maintenanceData)
    line3.set_data(timeData, rewardData)
    
def main(arguments):
    
    machineID = arguments[0]
    
    #define mqtt variables
    global rulValueTopic, rewardTopic, maintenanceActionTopic
    rulValueTopic = f"{machineID} predicted_rul"
    rewardTopic = f"{machineID} reward_value"
    maintenanceActionTopic = f"{machineID} tm choice"
    
    #set up mqtt connection 
    broker = "10.134.203.151"
    client_name = f'{machineID}_visualiser_rul'
    client = mqtt.Client(client_name)
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker)
    
    #set title
    fig.suptitle(f'Machine {machineID}')
    
    while True:
        client.loop_start()
        client.subscribe(rulValueTopic)
        client.subscribe(maintenanceActionTopic)
        client.subscribe(rewardTopic)
        client.on_message = on_message
        time.sleep(1)
        
        ani = animation.FuncAnimation(fig, animate, interval=1000)

        plt.show()
        
    return

if __name__ == "__main__":
    main(sys.argv[1:])
