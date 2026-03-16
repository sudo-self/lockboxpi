#!/bin/bash
echo "Setting up Apache SSL on port 8443..."

# Ensure modules are enabled
sudo a2enmod ssl
sudo a2enmod proxy
sudo a2enmod proxy_http

# Ensure we listen on 8443
if ! grep -q "Listen 8443" /etc/apache2/ports.conf; then
    echo "Listen 8443" | sudo tee -a /etc/apache2/ports.conf
fi

# Generate self-signed cert if missing
if [ ! -f /etc/ssl/certs/apache-selfsigned.crt ]; then
    sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/ssl/private/apache-selfsigned.key \
        -out /etc/ssl/certs/apache-selfsigned.crt \
        -subj "/C=US/ST=State/L=City/O=Lockbox/CN=lockboxpi.local"
fi

# Create 8443 VirtualHost
cat << 'EOF' | sudo tee /etc/apache2/sites-available/001-lockbox-ssl.conf
<VirtualHost *:8443>
    DocumentRoot /var/www
    
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/apache-selfsigned.crt
    SSLCertificateKeyFile /etc/ssl/private/apache-selfsigned.key

    <Directory /var/www>
        AllowOverride All
        Require all granted
    </Directory>

</VirtualHost>
EOF

# Enable site and restart apache
sudo a2ensite 001-lockbox-ssl.conf
