#!/bin/bash
PASS=$1
export MPLANE_DIR=$(pwd)
export MPLANE_PKI_DIR=$MPLANE_DIR/ca
MINIMUM_SIZE=1024
LOG_DIR="/var/log/syslog"
NODEID_PATH="/nodeid" 

echo "If there is an error,  check the log file $LOG_DIR"

if [ -s $NODEID_PATH ]
then
	read -r NODE_ID < $NODEID_PATH 2>>$LOG_DIR

else
	sudo bash get_node_id.sh 2>>$LOG_DIR
	read -r NODE_ID < $NODEID_PATH 2>>$LOG_DIR

fi

if [ -z $NODE_ID ]
then
	echo "There is NO NodeID to generate the certificcate!" 
	exit $?
fi

name="Monroe_Node_"$NODE_ID
#name="Monroe_Repository_"$NODE_ID

sed -i 's/commonName.*/commonName              =  \"'$name'\"/g' etc/component.conf 2>>$LOG_DIR
sed -i 's/SAN                     = DNS:.*/SAN                     = DNS:'$name'.POLITO.monroe.org/g' etc/component.conf 2>>$LOG_DIR

#sed -i 's/SAN                     = DNS:.*/SAN                     = DNS:monroe-repository.polito.it/g' etc/component.conf 2>>$LOG_DIR


echo "Creating TLS certificate request....."
openssl req -new -config $MPLANE_DIR/etc/component.conf -out $MPLANE_PKI_DIR/certs/${name}.csr -keyout $MPLANE_PKI_DIR/certs/${name}.key -passin pass:$PASS -passout pass:$PASS 2>>$LOG_DIR


echo "Creating TLS certificate....."

openssl ca  -passin pass:$PASS -config $MPLANE_DIR/etc/root-ca.conf -in $MPLANE_PKI_DIR/certs/${name}.csr -out $MPLANE_PKI_DIR/certs/${name}.crt -extensions server_ext 2>>$LOG_DIR << EOF
y
y
EOF

echo "Creating plaintext key....."

openssl pkey -in $MPLANE_PKI_DIR/certs/${name}.key -out $MPLANE_PKI_DIR/certs/${name}-plaintext.key -passin pass:$PASS 2>>$LOG_DIR


rm $MPLANE_PKI_DIR/certs/${name}.csr

if [ -s "$MPLANE_PKI_DIR/certs/$name.crt" -a \
	 -s "$MPLANE_PKI_DIR/certs/$name-plaintext.key" -a \
	 -s "$MPLANE_PKI_DIR/certs/$name.key" -a \
	 $(wc -c <"$MPLANE_PKI_DIR/certs/$name.crt") -ge $MINIMUM_SIZE -a \
	 $(wc -c <"$MPLANE_PKI_DIR/certs/$name-plaintext.key") -ge $MINIMUM_SIZE -a \
	 $(wc -c <"$MPLANE_PKI_DIR/certs/$name.key") -ge $MINIMUM_SIZE ]
then
  echo "Certificate succefully generated!"

fi

