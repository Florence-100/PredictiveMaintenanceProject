#mqtt imports 
import paho.mqtt.client as mqtt 
import tensorflow as tf
import numpy as np
import time
import sys
import datetime

#Configure GPU
gpus=tf.config.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.set_logical_device_configuration(gpus[0], [tf.config.LogicalDeviceConfiguration(memory_limit=25)])
        logical_gpus = tf.config.list_logical_devices('GPU')
        print(len(gpus), "Physical GPU", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        print(e)

#constants 
callForMaintenance = 'a1'
doNotMaintain = 'a0'
anomalyDetectionThreshold = 0.0838

#global variables 
sensorReadings = []
totalReward = 0
totalTimestepCounter = 0
decision_time = datetime.datetime.now()
initial = True

#mqtt topics set as global variables 
sensorReadingTopic = ""
maintenanceActionTopic = ""
rewardTopic = ""
currentStateTopic = ""

#flags to check for update 
newSensorReading = False 

#mqtt subscribe
def on_message(client, userdata, message):
    result = message.payload.decode("utf-8")
    topic = message.topic
    #check if in maintenance 
    global sensorReadings, totalReward, newSensorReading, totalTimestepCounter, decision_time
    if topic == sensorReadingTopic:
        noBracketResult = result[1:-1]
        formattedResult = noBracketResult.split(" ")
        formattedResult = list(filter(None, formattedResult))
        formattedResult = list(map(lambda x: float(x), formattedResult))
        totalTimestepCounter += 1
        if formattedResult[0] < 0:
            print("Machine is in maintenance")
            
            currentTime = datetime.datetime.now()

            #implement delay
            time_diff = (currentTime - decision_time).total_seconds()

            if time_diff<5:    
                wait_time = 5 - time_diff
                time.sleep(wait_time)

            #check time diff
            currentTime = datetime.datetime.now()
            time_diff = (currentTime - decision_time).total_seconds()
            print(f'Seconds elapsed {time_diff}')
            decision_time = datetime.datetime.now()
            
            client.publish(maintenanceActionTopic, callForMaintenance)
        else:
            result_arr = np.array(formattedResult)
            sensorReadings = result_arr.reshape(-1, 4) #Update global variable and flag
            newSensorReading = True 
    elif topic == rewardTopic:
        currentReward = message.payload.decode("utf-8")
        totalReward += int(currentReward)
        print("Total cummulative reward %d at timestep %d" % (totalReward, totalTimestepCounter))
    elif topic == currentStateTopic:
        currentState = int(message.payload.decode("utf-8"))
        print("Current machine state is %d" % currentState)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected OK')
    else:
        print('Bad connection Returned code = ' + str(rc))

def on_disconnect(client, userdata, flags, rc = 0):
    print('Disconnected result code: ' + str(rc))
            
    return

#anomaly detector
def isAnomaly(client, point, model):
    global currentAnomalyScore, decision_time
    predictions = model.predict(point)
    anomalyScore = (np.mean(np.power(point - predictions, 2), axis=1))**0.5
    anomalyScore = anomalyScore[0]
    
    currentTime = datetime.datetime.now()

    #implement delay
    time_diff = (currentTime - decision_time).total_seconds()

    if time_diff<5:    
        wait_time = 5 - time_diff
        time.sleep(wait_time)

    #check time diff
    currentTime = datetime.datetime.now()
    time_diff = (currentTime - decision_time).total_seconds()
    print(f'Seconds elapsed {time_diff}')
    decision_time = datetime.datetime.now()
    
    if anomalyScore > anomalyDetectionThreshold:
        print(f"Anomalous readings with anomaly score {anomalyScore}")
        client.publish(maintenanceActionTopic, callForMaintenance)
    else:
        print(f"All good with anomaly score {anomalyScore}")
        client.publish(maintenanceActionTopic, doNotMaintain)
    
    return

def anomalyAgent(client, machineIdentity, AD_model):
    #define mqtt variables 
    global sensorReadingTopic, maintenanceActionTopic, rewardTopic, newSensorReading, currentStateTopic, initial, sensorReadings
    sensorReadingTopic = f"{machineIdentity} sensor_obs_values"
    maintenanceActionTopic = f"{machineIdentity} tm choice"
    rewardTopic = f"{machineIdentity} reward_value"
    currentStateTopic = f"{machineIdentity} curr_state"
    
    while True:
        client.loop_start()
        client.subscribe(sensorReadingTopic)
        client.subscribe(rewardTopic)
        client.subscribe(currentStateTopic)
        client.on_message = on_message
        
        if initial:
            #initialise model first 
            dummy_arr = [0.5, 0.5, 0.5, 0.5]
            dummy_arr_NP = np.array(dummy_arr)
            dummy_arr_NP = dummy_arr_NP.reshape(1,4)
            isAnomaly(client, dummy_arr_NP, AD_model)
            isAnomaly(client, dummy_arr_NP, AD_model)
            initial=False

        if newSensorReading:
            isAnomaly(client, sensorReadings, AD_model)
            newSensorReading = False
                
        time.sleep(1)
    
    return

def main(arguments):
	#Update machine identity
	machineID = arguments[0] 	

	#load models 
	anomaly_clf = tf.keras.models.load_model('AE_tuneActivation_code_relu.h5')

	#connect mqtt 
	clientName = f"ZQ_AD_{machineID}"
	client = mqtt.Client(clientName)
	broker = "10.134.203.151" 
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.connect(broker) #connect to broker

	anomalyAgent(client, machineID, anomaly_clf)

	return 

if __name__ == "__main__":
    main(sys.argv[1:])
