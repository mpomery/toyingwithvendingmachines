crctab = []
CRC16 = 0x1021

def do_crc(message, crc = 0):
	for i in range(0,len(message)):
		crc = ((crc << 8) ^ (crctab[(crc >> 8) ^ ord(message[i])])) & 0xffff
	return crc

# Generate crctab
for val in range(0,256):
	crc = val << 8;
	for i in range(0,8):
		crc = crc << 1
		if (crc & 0x10000):
			crc = crc ^ CRC16
	crctab.append(crc & 0xffff)
