# -*- coding: utf-8 -*-
"""
Created on Thu Feb  3 13:37:32 2022

@author: NG ZHI QING
"""

import time
from collections import deque
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys

#graph variables
isAnomaly = 0
currentCummulativeReward = 0
timeCounter = 0
anomalyData = deque([isAnomaly])
rewardData = deque([currentCummulativeReward])
timeData = deque([timeCounter])

#mqtt topics 
maintenanceActionTopic = ""
rewardTopic = ""

#constants
maintenance = 'a1'
noMaintenance = 'a0'

#set up graphs 
fig, (ax1, ax2) = plt.subplots(2, sharex = True)
    
ax1.set_title('Anomaly/Maintenance')
ax2.set_title('Cummulative Rewards')
    
line1, = ax1.plot(timeData, anomalyData, c='blue')
line2, = ax2.plot(timeData, rewardData, c='red')

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
    global currentCummulativeReward, isAnomaly, timeCounter 
    if topic == maintenanceActionTopic:
        currentAction = message.payload.decode("utf-8")
        if currentAction == maintenance:
            isAnomaly = 1
        else:
            isAnomaly = 0 
    elif topic == rewardTopic:
        currentReward = message.payload.decode("utf-8")
        currentCummulativeReward += int(currentReward)
        timeCounter += 1
        print(f"Current cumulative reward is {currentCummulativeReward} at {timeCounter}")

def animate(i):

    global currentCummulativeReward, isAnomaly, timeCounter, timeData, anomalyData, rewardData, ax1, ax2, line1, line2

    timeData.append(timeCounter)
    anomalyData.append(isAnomaly)
    rewardData.append(currentCummulativeReward)

    ax1.set_ylim(bottom=-0.01, top=1.01)
    ax1.autoscale_view()
    ax2.relim()
    ax2.autoscale_view()
    
    line1.set_data(timeData, anomalyData)
    line2.set_data(timeData, rewardData)
    
def main(arguments):
    
    machineID = arguments[0]
    
    #define mqtt variables
    global maintenanceActionTopic, rewardTopic
    maintenanceActionTopic = f"{machineID} tm choice"
    rewardTopic = f"{machineID} reward_value"
    
    #set up mqtt connection 
    broker = "10.134.203.151"
    client_name = f'{machineID}_visualiser_ad'
    client = mqtt.Client(client_name)
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker)
    
    #set title
    fig.suptitle(f'Machine {machineID}')
    
    while True:
        client.loop_start()
        client.subscribe(maintenanceActionTopic)
        client.subscribe(rewardTopic)
        client.on_message = on_message
        time.sleep(1)
        
        ani = animation.FuncAnimation(fig, animate, interval=1000)

        plt.show()
        
    return

if __name__ == "__main__":
    main(sys.argv[1:])
