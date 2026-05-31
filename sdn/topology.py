#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

def create_topology():
    """
    Creates a simple tree topology with 1 switch and 4 hosts.
    Connects to a remote Ryu controller.
    """
    print("*** Creating network")
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)

    print("*** Adding controller (Ensure Ryu is running on port 6653)")
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    print("*** Adding hosts")
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')

    print("*** Adding switch")
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    print("*** Creating links")
    # Limiting bandwidth to simulate real scenarios
    net.addLink(h1, s1, bw=10)
    net.addLink(h2, s1, bw=10)
    net.addLink(h3, s1, bw=10)
    net.addLink(h4, s1, bw=10)

    print("*** Starting network")
    net.build()
    c0.start()
    s1.start([c0])

    print("*** Running CLI")
    CLI(net)

    print("*** Stopping network")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
