#!/usr/bin/env python3
import netmiko
import json
import time

with open("/path/to/creds.json") as credentials:
    creds = json.load(credentials)

name = creds["username"]
passwrd = creds["password"]
ios = "cisco_ios"
secret_passwrd = creds["enablepw"]

netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                      netmiko.ssh_exception.NetMikoAuthenticationException)


# Connection function to reuse in other parts/functions
def connector(device_ip):
    try:
        connection = netmiko.ConnectHandler(username=name, password=passwrd, device_type=ios, ip=device_ip,
                                            secret=secret_passwrd)
        if ">" in connection.find_prompt():
            connection.enable()
        return connection
    except netmiko_exceptions as e:
        print("Failed to ", device, e)


# Initial search object
class MacSearch:
    # Initialize object as well as set searching further to zero and the address being verified to zeor
    def __init__(self, search_more=0, verified=0):
        self.search_more = search_more
        self.verified = verified

    def nomore_search_more(self):
        self.search_more = 0
        return self.search_more

    def get_search_more(self):
        return self.search_more

    # Get interface where MAC address shows up on
    def mac_trace(self, mac_address):
        search_mac = connect.send_command('sh mac address-table | i {}'.format(mac_address))
        search_int = search_mac.split()[-1]
        return search_int

    # Check CDP neighbor info to see next device to connect to if necessary
    def get_cdp_neighbor(self, nei_interface):
        # Check if CDP neighbor is a switch
        cdp_info = connect.send_command('show cdp neighbors {} | i S I'.format(nei_interface))
        if cdp_info:
            # Attempt to grab the neighbor ID as well as the address of it
            neighbor_id = connect.send_command('show cdp neighbors {} det | i Device ID:'.format(nei_interface))
            addresses = connect.send_command('show cdp neighbors {} det | i IP address:'.format(nei_interface))
            try:
                neighbor = neighbor_id.split()[-1]
            except IndexError:
                neighbor = None
                pass
            try:
                address = addresses.splitlines()[0].split()[-1]
            except IndexError:
                address = None
                pass
            return neighbor, address
        else:
            neighbor = None
            address = None
            return neighbor, address

    # If interface is a port-channel, grab last member of channel to check for CDP info
    def get_port_channel_interface(self, port_channel):
        port_channel_start = port_channel.split()[-1]
        port_channel_members = connect.send_command('show interface {} | i Members'.format(port_channel_start))
        member = port_channel_members.split()[-1]
        return member

    def mac_address_input(self):
        mac_address = input('\r\nType in MAC address you want to search for (must be 12 hexadecimal characters): ')
        return mac_address

    # Attempt to convert MAC address to an integer in base 16
    # This will verify if characters are hex or not
    def char_validator(self, validate_mac):
        dividers = '.-: '
        new_mac = ''.join(c for c in validate_mac if c not in dividers)
        try:
            int(new_mac, 16)
            return True
        except ValueError:
            print('\r\nInvalid character detected')
            return None

    # Verify if MAC address is at 12 characters when dividers are removed
    def len_validator(self, validate_mac):
        dividers = '.-: '
        new_mac = ''.join(c for c in validate_mac if c not in dividers)
        if len(new_mac) != 12:
            print('\r\nMAC address is not the correct length')
            return None
        else:
            return True

    # Once MAC address is verified, this will format it to be 'Cisco' like
    def mac_formatter(self, unformatted_mac):
        dividers = '.-: '
        new_mac = ''.join(c for c in unformatted_mac if c not in dividers)
        formatted_mac = new_mac.lower()[0:4] + '.' + new_mac.lower()[4:8] + '.' + new_mac.lower()[8:]
        return formatted_mac


first_device_address = input('\r\nInput device hostname or IP address to start looking for a MAC address: ')
search = MacSearch(search_more=1)

# Will pass MAC address in various methods to determin if valid
while True:
    check_mac = search.mac_address_input()
    if not search.char_validator(check_mac):
        print('Input a valid MAC address...')
    elif not search.len_validator(check_mac):
        print('Input a valid MAC address...')
    else:
        mac = search.mac_formatter(check_mac)
        break

# Will start searching for a MAC address using first host provided
print('\r\nSearching for MAC address {}, standby...'.format(mac))
next_device = [first_device_address]
next_device_name = [first_device_address]  # Used only for showing name of device when address is found

# Loop through devices while searching for the address
while search.get_search_more() == 1:
    for device in next_device:
        try:
            connect = connector(device)
            interface = search.mac_trace(mac)
            if 'Po' in interface:  # If interface is a port-channel, will attempt to grab CDP info on member link
                neighbor_interface = search.get_port_channel_interface(interface)
                new_device_name, addy = search.get_cdp_neighbor(neighbor_interface)
                next_device[0] = addy  # Set next_device to CDP neighbor to log into next
                next_device_name[0] = new_device_name  # Set name to display next switch we'll connect to
                print('\r\nAddress is not on current device, will check on {}...'.format(new_device_name))
                connect.disconnect()
            else:
                new_device, addy = search.get_cdp_neighbor(interface)
                if not new_device and not addy:  # If CDP info is blank (no switch) address should be on this interface
                    print('\r\nMAC address is on device {} attached to interface {}'.format
                          (next_device_name, interface))
                    search.nomore_search_more()
                    connect.disconnect()
                else:
                    print('\r\nChecking interface {} for more info'.format(interface))
                    new_device_name, addy = search.get_cdp_neighbor(interface)
                    next_device[0] = addy  # Set next_device to CDP neighbor to log into next
                    next_device_name[0] = new_device_name  # Set name to display next switch we'll connect to
                    print('\r\nAddress is not on current device, will check on {}...'.format(new_device_name))
                    connect.disconnect()

        # If issue is that MAC address isn't found, will display a note and close out
        except IndexError:
            print('\r\nAddress not detected, try again later or make sure correct MAC address has been entered')
            print('\r\n***Note that this does not mean the device is not plugged in. It just means the switch has not'
                  ' seen the device yet or in the recent past***')
            search.nomore_search_more()
            connect.disconnect()
            break

# Quick hack as I had this script be the only thing a person could run when logged in and would close immediately
# after finishing
time.sleep(30)
