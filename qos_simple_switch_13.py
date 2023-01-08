# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

############################################################

#Francisco de Borja Esteban García
#Pablo Ruiz Giles

############################################################

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

portToVLANDict = {1: 1000, 2:500, 3:500, 4:1000, 5:500, 6:1000}

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    #Manjeador de mensajes FEATURE
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.

        #No hay coincidencias
        match = parser.OFPMatch()

        
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        #indica prioridad 0 y cualquier coincidencia
        #datapath=referencia del switch
        self.add_flow(datapath, 0, match, actions)


    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        #constantes
        ofproto = datapath.ofproto
        #decodificar
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    #Mensajes de entrada/PACKET_IN
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch


        

        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)

                             
        msg = ev.msg
        #Referencia al switch que envió el mensaje al controlador
        datapath = msg.datapath
        #constantes
        ofproto = datapath.ofproto
        #co descodificar
        parser = datapath.ofproto_parser
        #puerto de entrada
        in_port = msg.match['in_port']

        #contenido del paquete
        pkt = packet.Packet(msg.data)
        #campo ethernet
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        #MAC DESTINO
        dst = eth.dst
        #MAC ORIGEN
        src = eth.src
        #Identificador del switch
        dpid = datapath.id



        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        #Guarda dir MAC origen y puerto
        self.mac_to_port[dpid][src] = in_port
        
        
        
        actions = []
        unicast = True


        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]

            #Miramos que estamos en la misma VLAN
            if portToVLANDict[in_port] == portToVLANDict[out_port]:
                actions = [parser.OFPActionOutput(out_port)]

        else:
            out_port = ofproto.OFPP_FLOOD

            for variable in portToVLANDict:


                    self.logger.info("Valor vlan entrada y a comprobar %s %s ", portToVLANDict[in_port], portToVLANDict[variable])
                    
                    self.logger.info("Puerto vlan entrada y a comproabr  %s %s", in_port, variable)


                    if portToVLANDict[in_port] == portToVLANDict[variable] and in_port != variable:

                        out_port = variable

                        actions.append(parser.OFPActionOutput(out_port))
                        unicast = False

                 





        # install a flow to avoid packet_in next time

        if unicast == True:

            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
