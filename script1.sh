#!/bin/bash

#Arranque de escenarios VNX

cd /home/upm/shared/nfv-lab
sudo vnx -f vnx/nfv3_home_lxc_ubuntu64.xml -t
sudo vnx -f vnx/nfv3_server_lxc_ubuntu64.xml -t


#Destruir los escenearios VNX ---------era -P?
#cd /home/upm/shared/nfv-lab
#sudo vnx -f vnx/nfv3_home_lxc_ubuntu64.xml -P
#sudo vnx -f vnx/nfv3_server_lxc_ubuntu64.xml -P
