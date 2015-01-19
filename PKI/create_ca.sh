export MPLANE_DIR=$(pwd)
export MPLANE_PKI_DIR=$MPLANE_DIR/ca

echo "Creating CA directories..."

mkdir -p $MPLANE_PKI_DIR/root-ca/private ca/root-ca/db crl
mkdir -p $MPLANE_PKI_DIR/certs
chmod 700 $MPLANE_PKI_DIR/root-ca/private

echo "Creating CA database...."

cp /dev/null $MPLANE_PKI_DIR/root-ca/db/root-ca.db
cp /dev/null $MPLANE_PKI_DIR/root-ca/db/root-ca.db.attr
echo 01 > $MPLANE_PKI_DIR/root-ca/db/root-ca.crt.srl
echo 01 > $MPLANE_PKI_DIR/root-ca/db/root-ca.crl.srl

echo "Creating CA request...."

openssl req -new -config $MPLANE_PKI_DIR/etc/root-ca.conf -out $MPLANE_PKI_DIR/root-ca/root-ca.csr -keyout $MPLANE_PKI_DIR/root-ca/private/root-ca.key

echo "Creating CA certificate...."

openssl ca -selfsign -config $MPLANE_PKI_DIR/etc/root-ca.conf -in $MPLANE_PKI_DIR/root-ca/root-ca.csr -out $MPLANE_PKI_DIR/root-ca/root-ca.crt -extensions root_ca_ext


echo "Creating Signing CA directories..."

mkdir -p $MPLANE_PKI_DIR/signing-ca/private ca/signing-ca/db crl
chmod 700 $MPLANE_PKI_DIR/signing-ca/private

echo "Creating Signing CA database...."

cp /dev/null $MPLANE_PKI_DIR/signing-ca/db/signing-ca.db
cp /dev/null $MPLANE_PKI_DIR/signing-ca/db/signing-ca.db.attr
echo 01 > $MPLANE_PKI_DIR/signing-ca/db/signing-ca.crt.srl
echo 01 > $MPLANE_PKI_DIR/signing-ca/db/signing-ca.crl.srl

echo "Creating Signing CA request...."

openssl req -new -config $MPLANE_PKI_DIR/etc/signing-ca.conf -out $MPLANE_PKI_DIR/signing-ca/signing-ca.csr -keyout $MPLANE_PKI_DIR/signing-ca/private/signing-ca.key

echo "Creating Signing CA certificate...."

openssl ca -config $MPLANE_PKI_DIR/etc/root-ca.conf -in $MPLANE_PKI_DIR/signing-ca/signing-ca.csr -out $MPLANE_PKI_DIR/signing-ca/signing-ca.crt -extensions signing_ca_ext

echo "Creating PEM bundle...."

openssl x509 -in $MPLANE_PKI_DIR/signing-ca/signing-ca.crt -out $MPLANE_PKI_DIR/signing-ca/signing-ca.pem -outform PEM
openssl x509 -in $MPLANE_PKI_DIR/root-ca/root-ca.crt -out $MPLANE_PKI_DIR/root-ca/root-ca.pem -outform PEM
cat  $MPLANE_PKI_DIR/signing-ca/signing-ca.pem $MPLANE_PKI_DIR/root-ca/root-ca.pem > $MPLANE_PKI_DIR/ca-chain.pem

echo "CA successfully created"
echo "Use the file [$MPLANE_PKI_DIR/ca-chain.pem] as ca-chain parameter in client/server command line parameter"

