sudo cp deploy/nginx/tngd-defence.conf /etc/nginx/sites-available/tngd-defence.conf
sudo ln -sf /etc/nginx/sites-available/tngd-defence.conf /etc/nginx/sites-enabled/tngd-defence.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx