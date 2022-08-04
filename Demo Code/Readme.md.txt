This file contains code used for the integrated testbed. 

anomaly_detection_AE.py 
Code for anomaly detection model with autoencoders
To run, key in terminal python3 anomaly_detection_AE.py F1M1 where F1M1 is the machine name 

RUL_SVR.py 
Code for RUL estimation model with support vector regressor 
To run, key in terminal python3 RUL_SVR.py F1M1 where F1M1 is the machine name

The two codes above implement time checkers to make sure that new decisions are sent every 5s to ensure consistency across intelligent agents
and not overwhelm the physical layer. 

machine_visualisation_ad.py 
Code for visualisation of anomaly detection model performance with Matplotlib Animation 
To run, key in terminal python3 machine_visualisation_ad.py F1M1, where F1M1 is the machine name 

machine_visualisation_rul.py 
Code for visualisation of RUL estimation model performance with Matplotlib Animation
To run, key in terminal python3 machine_visualisation_rul.py F1M1, where F1M1 is the machine name 

anomaly_detection_AE.py and RUL_SVR.py conduct some analysis of dummy readings to initialise the anomaly detection model to avoid delays in
integrated testbed. Thus, machine_visualisation_ad.py and machine_visualisation_rul.py needs to be run some time after anomaly_detection_AE.py and 
RUL_SVR.py finish processing the dummy values. This can be determined through the terminal outputs. All codes need to be run before the physical layer 
starts. 