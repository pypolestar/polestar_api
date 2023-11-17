# polestar_api
Polestar API

This application is not an official app affiliated with Polestar.


## Create a Polestar/Volvo Account
First you need to create a Polestar Developer account on this website: 
https://developer.volvocars.com/apis/extended-vehicle/v1/overview/
on your right side you can choose "Sign Up" and just follow the step.

## Create 'vcc_api_key'
Sign into your Polestar Account and go to your account:
https://developer.volvocars.com/account/
Create a new Application. In my case it call 'My Polestar'

![image](https://github.com/leeyuentuen/polestar_api/assets/1487966/1e4694fe-90ee-4915-b198-55d6b084dc50)

After create, you will see 2 vcc_api_key

![image](https://github.com/leeyuentuen/polestar_api/assets/1487966/b660dffb-096d-4a15-afaa-7213fff24359)


## Add in HA Integration
Add custom repository in HACS: https://github.com/leeyuentuen/polestar_api
Search for integration 'polestar_api'

and fill the information:
email and password: are these from your polestar developer account
VIN: is the car identification number that you can find in your polestar app or polestar account
VCC api key: the key above that you have generate (i've take the first one)

![image](https://github.com/leeyuentuen/polestar_api/assets/1487966/11d7586b-9d88-4b65-bd2b-0c5f66ff52fa)

![image](https://github.com/leeyuentuen/polestar_api/assets/1487966/a8ae1b78-912b-40b5-9498-2534b07f4200)
