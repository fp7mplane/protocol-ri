#!/bin/bash
NODE_ID=$1
PASS=$2
DN="Monroe_Supervisor_POLITO_"$NODE_ID
export MPLANE_DIR=$(pwd)
export MPLANE_PKI_DIR=$MPLANE_DIR/ca
MINIMUM_SIZE=1024


echo "Enter certificate name: "
read name <<EOF 
$DN
EOF

sed -i 's/commonName.*/commonName              =  \"'$DN'\"/g' etc/supervisor.conf
#sed -i 's/SAN                     = DNS:.*/SAN                     = DNS:'$DN'.POLITO.monroe.org/g' etc/supervisor.conf
sed -i 's/SAN                     = DNS:.*/SAN                     = DNS:monroe-supervisor.polito.it/g' etc/supervisor.conf



echo "Creating TLS certificate request....."
openssl req -new -config $MPLANE_DIR/etc/supervisor.conf -out $MPLANE_PKI_DIR/certs/${name}.csr -keyout $MPLANE_PKI_DIR/certs/${name}.key -passin pass:$PASS -passout pass:$PASS


echo "Creating TLS certificate....."

openssl ca  -passin pass:$PASS -config $MPLANE_DIR/etc/root-ca.conf -in $MPLANE_PKI_DIR/certs/${name}.csr -out $MPLANE_PKI_DIR/certs/${name}.crt -extensions server_ext << EOF
y
y
EOF

echo "Creating plaintext key....."

openssl pkey -in $MPLANE_PKI_DIR/certs/${name}.key -out $MPLANE_PKI_DIR/certs/${name}-plaintext.key -passin pass:$PASS


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
