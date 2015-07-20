# Simple instructions for Certificate Generation Scripts

There are three .sh scripts in this folder:
- create-component-cert.sh
- create-client-cert.sh
- create-supervisor-cert.sh
- create-ca.sh (this one should not be used, see [Generating a new CA](#new_CA) below for more info)
In the ./etc/ folder there are the configuration files for each of those scripts.

###Generating a certificate

To generate a certificate (e.g. a component certificate), follow these steps:
1. open the corresponding configuration file (./etc/component.conf)
2. modify the SAN field (e.g. replace DNS:Supervisor-1.SSB.mplane.org with DNS:Supervisor-1.Polito.mplane.org)
3. modify the fields in the [component_dn] section (you will be prompted for these 
   fields while running the script, so you can also modify them later)
4. run create-component-cert.sh and follow the instructions:
	- enter filename of your certificate
	- enter PEM passphrase (passphrase to open your encrypted certificate)
	- enter the Distinguished Name
	- enter the root-ca passphrase 
	  (send a mail to stefano.pentassuglia@ssbprogetti.it to know that)
	- re-enter PEM passphrase
5. Certificate created in PKI/ca/certs/

<a name="new_CA"></a>
###Generating a new CA:

_IMPORTANT_: You can create your own CA and generate certificates dependent from that CA, but these will not be compatible with the other mPlane certificates. If you want to keep compatibility, use the provided CA (follow the steps above)

To generate a new CA, run create-ca.sh and follow the instructions:
- enter PEM passphrase (passphrase to open your encrypted certificate)
- re-enter PEM passphrase
The certificate will be created in PKI/ca/root-ca/, and the directory structure for the PKI will also be created in PKI/ca/
