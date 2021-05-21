#!/bin/sh


# Hardcoding LACP to none for now
# May need to revisit later
TMODE="none"
UPLINK='eth'

if [ -z "$TMODE" ]; then
  TMODE='none'
  
fi


#######################
# Re-run script as sudo
#######################

if [ "$(id -u)" != "0" ]; then
  exec sudo "$0" "$@"
fi

###############
# Enabling LLDP
###############

lldpad -d
for i in `ls /sys/class/net/ | grep 'eth\|ens\|eno'`
do
    lldptool set-lldp -i $i adminStatus=rxtx
    lldptool -T -i $i -V sysName enableTx=yes
    lldptool -T -i $i -V portDesc enableTx=yes
    lldptool -T -i $i -V sysDesc enableTx=yes
done

################
# Teaming setup
################

cat << EOF > /home/alpine/teamd-lacp.conf
{
   "device": "team0",
   "runner": {
       "name": "lacp",
       "active": true,
       "fast_rate": true,
       "tx_hash": ["eth", "ipv4", "ipv6"]
   },
     "link_watch": {"name": "ethtool"},
     "ports": {"eth1": {}, "eth2": {}}
}
EOF

cat << EOF > /home/alpine/teamd-static.conf
{
 "device": "team0",
 "runner": {"name": "roundrobin"},
 "ports": {"eth1": {}, "eth2": {}}
}
EOF

if [ "$TMODE" == 'lacp' ]; then
  TARG='/home/alpine/teamd-lacp.conf'
elif [ "$TMODE" == 'static' ]; then
  TARG='/home/alpine/teamd-static.conf'
fi

if [ "$TMODE" == 'lacp' ] || [ "$TMODE" == 'static' ]; then
  teamd -v
  ip link set eth1 down
  ip link set eth2 down
  teamd -d -f $TARG

  ip link set team0 up
  UPLINK="team"
fi

################
# IP addr setup
################



cat << EOT >> /set_ips.sh
#!/bin/sh
args="$@"
for arg in \$args; do
  eval ip=\`echo \$arg | cut -d':' -f2\`
  eval int=\`echo \$arg | cut -d':' -f1\`
  eval netw=\`echo \$arg | cut -d':' -f3\`
  eval gw=\`echo \$ip | cut -d'.' -f1-3\`
  sudo ip addr flush dev \$int
  sudo ip addr add \$ip dev \$int
  if [ -z "\$netw" ] 
  then
    sudo ip route add default via \$gw.1
  else
    n=\$(echo \$netw | tr "," "\n")
    for i in \$n
    do
      sudo ip route add \$i via \$gw.1
    done
  fi
done
EOT

chmod +x /set_ips.sh

/set_ips.sh

#####################
# Starting SSH server
#####################

if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
	# generate fresh rsa key
	ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa
fi
if [ ! -f "/etc/ssh/ssh_host_dsa_key" ]; then
	# generate fresh dsa key
	ssh-keygen -f /etc/ssh/ssh_host_dsa_key -N '' -t dsa
fi

if [ ! -d "/var/run/sshd" ]; then
  mkdir -p /var/run/sshd
fi

/usr/sbin/sshd -D -e -f /etc/ssh/sshd_config
