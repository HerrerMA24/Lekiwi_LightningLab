#!/bin/bash
# =============================================================================
# Generate certificates for AWS Client VPN (Mutual TLS Authentication)
# Run this ONCE on your local machine, then upload server cert to ACM
# =============================================================================

set -e

CERT_DIR="./vpn-certs"
mkdir -p "$CERT_DIR"

# Clone easy-rsa if not present
if [ ! -d "$CERT_DIR/easy-rsa" ]; then
    git clone https://github.com/OpenVPN/easy-rsa.git "$CERT_DIR/easy-rsa"
fi

cd "$CERT_DIR/easy-rsa/easyrsa3"

# Initialize PKI
./easyrsa init-pki

# Build CA (no password for automation — add one for production)
./easyrsa --batch build-ca nopass

# Generate server certificate
./easyrsa --batch build-server-full server nopass

# Generate client certificate (for the Pi)
./easyrsa --batch build-client-full lekiwi-pi nopass

# Copy certs to output directory
cd ../../..
mkdir -p "$CERT_DIR/output"
cp "$CERT_DIR/easy-rsa/easyrsa3/pki/ca.crt" "$CERT_DIR/output/"
cp "$CERT_DIR/easy-rsa/easyrsa3/pki/issued/server.crt" "$CERT_DIR/output/"
cp "$CERT_DIR/easy-rsa/easyrsa3/pki/private/server.key" "$CERT_DIR/output/"
cp "$CERT_DIR/easy-rsa/easyrsa3/pki/issued/lekiwi-pi.crt" "$CERT_DIR/output/"
cp "$CERT_DIR/easy-rsa/easyrsa3/pki/private/lekiwi-pi.key" "$CERT_DIR/output/"

echo ""
echo "============================================"
echo "Certificates generated in: $CERT_DIR/output/"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Upload server cert + key + CA to ACM:"
echo "   aws acm import-certificate \\"
echo "     --certificate fileb://$CERT_DIR/output/server.crt \\"
echo "     --private-key fileb://$CERT_DIR/output/server.key \\"
echo "     --certificate-chain fileb://$CERT_DIR/output/ca.crt \\"
echo "     --region us-east-1"
echo ""
echo "2. Upload client cert + CA to ACM (for Client VPN):"
echo "   aws acm import-certificate \\"
echo "     --certificate fileb://$CERT_DIR/output/lekiwi-pi.crt \\"
echo "     --private-key fileb://$CERT_DIR/output/lekiwi-pi.key \\"
echo "     --certificate-chain fileb://$CERT_DIR/output/ca.crt \\"
echo "     --region us-east-1"
echo ""
echo "3. Note the ACM ARNs — you'll need them for CloudFormation"
