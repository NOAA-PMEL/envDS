HTTPS
This Tomcat container can support HTTPS for either self-signed certificates which can be useful for experimentation or certificates from a CA for a production server. For a complete treatment on this topic, see https://tomcat.apache.org/tomcat-8.5-doc/ssl-howto.html.


Self-signed Certificates
This Tomcat container can support HTTP over SSL. For example, generate a self-signed certificate with openssl (or better yet, obtain a real certificate from a certificate authority):

openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 -subj \
    "/C=US/ST=Colorado/L=Boulder/O=Unidata/CN=tomcat.example.com" -keyout \
    ./ssl.key -out ./ssl.crt
Then augment the server.xml from this repository with this additional XML snippet for Tomcat SSL capability:

<Connector port="8443"
       maxThreads="150"
       enableLookups="false"
       disableUploadTimeout="true"
       acceptCount="100"
       scheme="https"
       secure="true"
       SSLEnabled="true"
       SSLCertificateFile="${catalina.base}/conf/ssl.crt"
       SSLCertificateKeyFile="${catalina.base}/conf/ssl.key" />