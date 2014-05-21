export MPLANE_DIR=$(pwd)
export MPLANE_PKI_DIR=$MPLANE_DIR/ca

echo "Enter private key name (no extension): "
read name
openssl pkey -in $MPLANE_PKI_DIR/certs/${name}.key -out $MPLANE_PKI_DIR/certs/${name}-plaintext.key
