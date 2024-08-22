This is what I did, more-or-less:

- Remove whatever default user it forced you to make.
- Remove Network Manager:
  ```
  # systemctl stop NetworkManager.service
  # systemctl disable NetworkManager.service
  # apt remove network-manager
  ```
- Add the IP address in `/etc/network/interfaces`:
  ```
  auto eth0
  iface eth0 inet static
      address 10.187.2.56/16
      gateway 10.187.0.1
  ```
- Fill in `/etc/resolv.conf`:
  ```
  search mit.edu
  nameserver 8.8.8.8
  nameserver 8.8.4.4
  ```
- Deal with time, install stuff, clean up, etc.:
  ```
  # timedatectl set-timezone America/New_York
  # timedatectl timesync-status
  # apt update
  # apt upgrade
  # apt install vim mosh tmux krb5-user zephyr-clients nginx python3-gpiozero python3-pymysql git
  # apt autoremove
  # systemctl start zhm.service
  ```
    - The default realm is `ATHENA.MIT.EDU`.
- Set up doorpi config in `/etc/doorpi`:
  ```
  sql.mit.edu
  sipb-door
  <mysql password>
  sipb-door+doorpi
  ```
- Clone, install, and run the code:
  ```
  # cd
  # git clone 'https://github.com/sipb/doorpi2'
  # cd doorpi2/sensor
  # sh < SETUP
  ```
- Set up nginx redirect:
  ```
  # rm /etc/nginx/sites-enabled/default
  # cat > /etc/nginx/site-available/redirect <<EOF
  server {
  	listen 80 default_server;
  	listen [::]:80 default_server;
  	server_name _;
  	rewrite ^.*$ https://sipb-door.mit.edu redirect;
  }
  EOF
  # ln -s /etc/nginx/sites-available/redirect /etc/nginx/sites-enabled/redirect
  # systemctl enable nginx
  # systemctl restart nginx
  ```
