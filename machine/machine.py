import socket
from time import sleep
from VendingMachine import VendingMachine


"""
Set up the connection to the vending machine. You shouldn't need to edit this code
"""
def connect_to_vendingmachine():
	print("Connecting to Virtual Vending Machine")
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
	sock.connect(('localhost', 5150))
	rfh = sock.makefile('r')
	wfh = sock.makefile('w')
	print("Connected")
	return rfh, wfh

"""
This is the main part of the program
"""
def main():
	# Connect to the vending machine
	rfh, wfh = connect_to_vendingmachine()
	vm = VendingMachine(rfh, wfh)

	# Anything you want to do prior to starting your program should happen here
	while True:
		# Everything you want to run continuously should go here
		for i in ["/LOADING\\", "-LOADING-", "\\LOADING/", "|LOADING|"]:
			vm.display(i)
			sleep(0.5)
		vm.vend("99")
		vm.display("BEEP")
		vm.beep()
		in1 = vm.get_key()
		vm.display("SELECT:" + str(in1))
		in2 = vm.get_key()
		vm.display("SELECT:" + str(in1) + str(in2))

if __name__=='__main__':
	main()
