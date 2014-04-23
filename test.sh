#!bin/sh

if [[ $1 == "True"  ||  $1 == "False" ]]; then
	echo "Proto = HTTP, Security = $1"
else
	echo "Parameter security missing or wrong value. Possible values: True or False"
	exit
fi
echo " "
echo "#######################################################################################"
echo "#########################   Test: Ping Probe + Client   ###############################"
echo "#######################################################################################"
echo " "
echo "##############################   Launching Server:   ##################################"
if [ $1 == "True" ]; then
	python3 -m mplane.ping --ip4addr 192.168.10.10 --sec 0 &
else
	python3 -m mplane.ping --ip4addr 192.168.10.10 --sec 1 &
fi
PID=$(pidof python3)
sleep 2

echo " "
echo "##############################   Launching Client:   ##################################"
expect ./test-client-process.sh $1

echo " "
echo "###############################   Killing Server:   ###################################"
sudo kill -9 $PID

echo " "
echo "#################################   End of Test   #####################################"
