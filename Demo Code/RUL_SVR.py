#mqtt imports 
import paho.mqtt.client as mqtt 
from joblib import load
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
RULthreshold = 5.500581
episodeCounterOffset = 3 #+1-3=-2

#global variables 
totalReward = 0
currentSensorReading = []
episodeTimeCounter = 0
machineFail = False
machineInMaintenance = False
totalTimestepCounter = 0
decision_time = datetime.datetime.now()
initial = True

#flags to check for update 
newSensorReading = False 

#mqtt topics set as global variables 
sensorReadingTopic = ""
maintenanceActionTopic = ""
rewardTopic = ""
currentStateTopic = ""
rulValueTopic = ""

#mqtt subscribe
def on_message(client, userdata, message):
    topic = message.topic
    #check if in maintenance 
    global newSensorReading, totalReward, currentSensorReading, episodeTimeCounter, machineFail, totalTimestepCounter, machineInMaintenance, decision_time
    if topic == sensorReadingTopic:
        result = message.payload.decode("utf-8")
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

            if not machineInMaintenance: 
                if episodeTimeCounter >= episodeCounterOffset:
                    episodeTimeCounter -= episodeCounterOffset
                else:
                    episodeTimeCounter = 0 #time must be positive
            machineInMaintenance = True
        else:
            machineInMaintenance = False 
            if not (machineFail):
                newSensorReading = True 
                currentSensorReading = formattedResult
    elif topic == rewardTopic:
        currentReward = message.payload.decode("utf-8")
        totalReward += int(currentReward)
        print("Total cummulative reward %d at timestep %d" % (totalReward, totalTimestepCounter))

        #update counters 
        if machineFail:
            machineFail = False
            episodeTimeCounter = 0

    elif topic == currentStateTopic:
        machineState = int(message.payload.decode("utf-8"))
        if machineState > 7:

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
            print(f"Machine in failure at state {machineState}")
            machineFail = True
        else:
            print("Current machine state is %d" % machineState)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected OK')
    else:
        print('Bad connection Returned code = ' + str(rc))

def on_disconnect(client, userdata, flags, rc = 0):
        print('Disconnected result code: ' + str(rc))

def isAnomaly(point, model):
    predictions = model.predict(point)
    anomalyScore = (np.mean(np.power(point - predictions, 2), axis=1))**0.5
    anomalyScore = anomalyScore[0]
    if anomalyScore > anomalyDetectionThreshold: #is anomaly
        return 1
    else:
        return 0
        
def predictRUL(client, readings, RUL_model):
    print(readings)
    global decision_time
    sensor_arr = np.array([readings])
    predictedValue = RUL_model.predict(sensor_arr)
    predictedValue = round(predictedValue[0], 4)
    print("Predicted RUL Value %f" % predictedValue)
    predictedValueString = str(predictedValue)
    client.publish(rulValueTopic, predictedValueString)

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
    
    if predictedValue < RULthreshold:
        print("Send machine for maintenance")
        client.publish(maintenanceActionTopic, callForMaintenance)
    else:
        client.publish(maintenanceActionTopic, doNotMaintain)
    
    return 

def RULpredictionAgent(client, machineIdentity, RUL_model, anomaly_model):
    #define mqtt variables 
    global sensorReadingTopic, maintenanceActionTopic, rewardTopic, rulValueTopic, newSensorReading, currentStateTopic, currentSensorReading, episodeTimeCounter, initial
    sensorReadingTopic = f"{machineIdentity} sensor_obs_values"
    maintenanceActionTopic = f"{machineIdentity} tm choice"
    rewardTopic = f"{machineIdentity} reward_value"
    currentStateTopic = f"{machineIdentity} curr_state"
    rulValueTopic = f"{machineIdentity} predicted_rul"

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
            dummyAnomalyStatus = isAnomaly(dummy_arr_NP, anomaly_model)
            dummyArr = [*dummy_arr, 10, dummyAnomalyStatus]
            predictRUL(client, dummyArr, RUL_model)
            predictRUL(client, dummyArr, RUL_model)
            initial=False
        
        if newSensorReading:
            newSensorReading = False
            currentSensorReadingArr = np.array(currentSensorReading)
            currentSensorReadingArr = currentSensorReadingArr.reshape(1,4)
            anomalyStatus = isAnomaly(currentSensorReadingArr, anomaly_model)
            infoArr = [*currentSensorReading, episodeTimeCounter, anomalyStatus] 
            predictRUL(client, infoArr, RUL_model)
            episodeTimeCounter += 1
            
        time.sleep(1)
        
    return

def main(arguments):
    #Update machine identity
	machineID = arguments[0] 
    
    #load scaler, anomaly detector, RUL predictor
	anomalyDetector = tf.keras.models.load_model('AE_tuneActivation_code_relu.h5')
	RULpredictor = load('SVR_rulModel_tuned_time_skv21.joblib')
    
    #connect mqtt 
	clientName = f"ZQ_RUL_{machineID}"
	client = mqtt.Client(clientName)
	broker = "10.134.203.151"
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.connect(broker) #connect to broker
   
	RULpredictionAgent(client, machineID, RULpredictor, anomalyDetector)
    
	return

if __name__ == "__main__":
	main(sys.argv[1:])
    
