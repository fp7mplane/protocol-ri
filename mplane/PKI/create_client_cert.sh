export MPLANE_DIR=$(pwd)
export MPLANE_PKI_DIR=$MPLANE_DIR/ca

echo "Enter certificate name: "
read name

echo "Creating TLS server certificate request....."
openssl req -new -config $MPLANE_PKI_DIR/etc/client.conf -out $MPLANE_PKI_DIR/certs/${name}.csr -keyout $MPLANE_PKI_DIR/certs/${name}.key

echo "Creating TLS server certificate....."

openssl ca -config $MPLANE_PKI_DIR/etc/signing-ca.conf -in $MPLANE_PKI_DIR/certs/${name}.csr -out $MPLANE_PKI_DIR/certs/${name}.crt
echo "Client certificate successfully created in: $MPLANE_PKI_DIR/certs/${name}.crt"
echo "Client private key successfully created in: $MPLANE_PKI_DIR/certs/${name}.key"
