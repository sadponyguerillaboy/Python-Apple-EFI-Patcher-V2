import binascii
import getopt
import json
import sys
from termcolor import colored
from urllib.request import urlopen
from xml.etree import ElementTree

def search_json_last4(json_object, hwc_code):
	for dict in json_object:
		if dict['last4'] == hwc_code:
			return dict['name']

# function adapted from MacmodelShelf - https://github.com/MagerValp/MacModelShelf
def lookup_mac_model_code_from_apple(model_code):
	try:
		f = urlopen("http://support-sp.apple.com/sp/product?cc=%s&lang=en_US" % model_code, timeout=2)
		et = ElementTree.parse(f)
		return et.findtext("configCode")
	except:
		return None

def search_and_update_db(json_db, hwc_code, destination_file):
	with open(json_db, 'rb') as db:
		json_database = json.load(db)
		db.close()

	search = search_json_last4(json_database, hwc_code)

	if search is None:
		model_info = lookup_mac_model_code_from_apple(hwc_code)

		if model_info != None:
			with open(destination_file, "w") as write_file:
				entry = {"last4": hwc_code, "name": model_info, "id": None, "modelnum": None}
				json_database.append(entry)
				sorted_database = sorted(json_database, key = lambda i: i['last4'])
				json.dump(sorted_database, write_file, indent=3)
			
			search_message = 'Database Updated with New Model Info'
		else:
			search_message = colored('Unable to Retrieve Identifier or HWC Invalid, Database Not Updated', 'red')
		return model_info, search_message

	else:
		model_info = search
		search_message = 'Identifier Info Found in Database'
		return model_info, search_message

def main(argv):

	# Variable Initialization
	clearNvram = False
	removeFirmwareLock = False
	writeFsys = False
	database = 'database.json'

	# Command Line Arguments
	try:
		opts, args = getopt.getopt(argv,"hnli:o:s:m:",["ifile=","ofile=","newSerial=","regionFilename="])
	except getopt.GetoptError:
		print ('patcher.py -i <input filename> -o <output filename> -s <serial to insert> -m <me region file> -n -l')
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print ('Usage: patcher.py -i <input filename> -o <output filename> -s <serial to insert> -m <me region file> -n -l')
			print ()
			print ('Options:')
			print ('-i <input filename>	-- name of the file to be modified')
			print ('-o <output filename>	-- name of the newly modified file')
			print ('-s <serial to insert>	-- serial number to be inserted')
			print ('-m <me region file>	-- name of the me region file to insert')
			print ('-n   			-- clear NVRAM')
			print ('-l   			-- remove firmware lock')
			print ()
			sys.exit()
		elif opt in ('-i', '--ifile'):
			inputfile = arg
		elif opt in ('-o', '--ofile'):
			outputfile = arg
		elif opt in ('-s', '--newSerial'):
			newSerial = arg
		elif opt in ('-m', '--regionFilename'):
			regionFilename = arg
		elif opt in ('-n'):
			clearNvram = True
		elif opt in ('-l'):
			removeFirmwareLock = True

	# Patch Serial Variable Initialization
	try:
		newSerial
	except NameError:
		print('Serial Patch Option Not Set - Skipping')
	else:
		patchSerial = (newSerial.upper()).encode('utf-8')
		patchHwc = ((newSerial[-4:]).upper()).encode('utf-8')
	

	# If inputfile exists try to open and read
	try:
		inputfile
	except NameError:
		print(colored('Error: Input File Not Set!', 'red'))
	else:
		try:
			with open(inputfile, 'rb') as content:

				entire_efi = content.read()

				# ME Region Offsets
				# if find function returns -1 then it means the searched value was not found
				meRegionOffsetV1 = entire_efi.find(b'\x20\x20\x80\x0F\x40\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x24\x46\x50\x54')
				meRegionOffsetV2 = entire_efi.find(b'\x20\x20\x80\x0F\x40\x00\x00\x24\x00\x00\x00\x00\x00\x00\x00\x00\x24\x46\x50\x54')
				meRegionOffsetV3 = entire_efi.find(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x24\x46\x50\x54')

				# NVRam Offsets
				nvramStartOffset = entire_efi.find(b'$VSS')
				nvramEndOffset = entire_efi.find(b'$VSS', nvramStartOffset + 4)

				# Fsys Offsets
				fsysStartOffset = entire_efi.find(b'Fsys')
				fsysEndOffset = entire_efi.find(b'EOF', fsysStartOffset + 4)
				ssnOffset = entire_efi.find(b'ssn', fsysStartOffset + 4, fsysEndOffset)
				SSN_Offset = entire_efi.find(b'SSN', fsysStartOffset + 4, fsysEndOffset)
				hwcOffset = entire_efi.find(b'hwc', fsysStartOffset + 4, fsysEndOffset)
				HWC_Offset = entire_efi.find(b'HWC', fsysStartOffset + 4, fsysEndOffset)
				sonOffset = entire_efi.find(b'son', fsysStartOffset + 4, fsysEndOffset)
				SON_Offset = entire_efi.find(b'SON', fsysStartOffset + 4, fsysEndOffset)

				# If Fsys Found
				# Search for Fsys CRC Offset (After EOF in Fsys, all bytes are 0x00 until CRC. Search until find a byte that is not 0x00)
				if fsysStartOffset != -1 and fsysEndOffset != -1:
					insideByte = b'\x00'
					compareByte = b'\x00'
					seekCounter = 3
					while (insideByte == compareByte):
						# Update crc32 offset to current byte being read
						crc32Offset = content.tell()
						content.seek(fsysEndOffset + seekCounter)
						holder = content.read(1)
						insideByte = holder
						seekCounter += 1

					# Extract Original CRC32 Value
					content.seek(crc32Offset)
					crcOriginal = content.read(4)
					crcOriginalReversed = binascii.hexlify((crcOriginal[::-1]))

					# Create Variable containing contents of Fsys Block to allow for CRC32 calculation
					content.seek(fsysStartOffset)
					fsysBlock = content.read(crc32Offset - fsysStartOffset)
					verifyOriginalCRC = '{:02x}'.format(binascii.crc32(fsysBlock) & 0xffffffff) #mask output to maintain format
				else:
					print(colored('Error: Unable to Locate Fsys Block inside File', 'red'))

				# Firmware Lock Offsets
				lockStartOffset = entire_efi.find(b'$SVS')
				lockEndOffset = entire_efi.find(b'$SVS', lockStartOffset + 4)

				if SSN_Offset != -1:
					content.seek(SSN_Offset + 5)
					serialOriginalUppercase = content.read(12)
					print('Original Serial in SSN Field: ', colored(serialOriginalUppercase.decode('utf-8'), 'yellow'))
				if ssnOffset != -1:
					content.seek(ssnOffset + 5)
					serialOriginalLowercase = content.read(12)
					print('Original Serial in ssn Field: ', colored(serialOriginalLowercase.decode('utf-8'), 'yellow'))
				if HWC_Offset != -1:
					content.seek(HWC_Offset + 5)
					HWC_Code = content.read(4)
					print('Original HWC Code in HWC Field: ', colored(HWC_Code.decode('utf-8'), 'yellow'))
				if hwcOffset != -1:
					content.seek(hwcOffset + 5)
					hwcCode = content.read(4)
					print('Original HWC Code in hwc Field: ', colored(hwcCode.decode('utf-8'), 'yellow'))
				if sonOffset != -1:
					content.seek(sonOffset + 5)
					sonCode = content.read(9)
					print('Original Model: ', colored(sonCode.decode('utf-8'), 'yellow'))

				print('Original Fsys CRC32: ', colored(crcOriginalReversed.upper().decode('utf-8'), 'yellow'))
				print('Recalculation of Fsys CRC32: ', colored(verifyOriginalCRC.upper(), 'yellow'))

				if crcOriginalReversed.decode('utf-8') == verifyOriginalCRC:
					print(colored('Original Fsys Checksum Valid!', 'green'))
				else:
					print(colored('Original Fsys Checksum Invalid - Mismatch!', 'red'))

				# Look up Identifier Associated with Origianl Serial & HWC
				origModel, searchOrigMessage = search_and_update_db(database, hwcCode.decode("utf-8"), database)
				print('Original Identifier: ', colored(origModel, 'yellow'))
				print(searchOrigMessage)

		except FileNotFoundError:
			print(colored('Input EFI File not found', 'red'))

	# Get ME Region File
	try:
		regionFilename
	except NameError:
		print('ME Region Patch Option Not Set - Skipping')
	else:
		try:
			with open(regionFilename, 'rb') as regionFile:
				patchRegion = regionFile.read()
		except FileNotFoundError:
			print(colored('Input ME File not found', 'red'))
	
	# Patch Fsys
	# If Serial Option Activated
	try:
		newSerial and inputfile
	except NameError:
		print('Serial Patch Option Not Set - Skipping')
	else:
		if len(newSerial) == 12:
			# Each serial instance (ssn, SSN & associated hwc & HWC) is patched individually, due to the fact you may have multiple serials in the Fsys Block due to
			# using an application like Blank Board Serializer or other patching applications.
			if SSN_Offset != -1:
				patchedFsys1 = fsysBlock.replace(serialOriginalUppercase, patchSerial)
			else:
				patchedFsys1 = fsysBlock

			if ssnOffset != -1:
				patchedFsys2 = patchedFsys1.replace(serialOriginalLowercase, patchSerial)
			else:
				patchedFsys2 = patchedFsys1	

			if HWC_Offset != -1:
				patchedFsys3 = patchedFsys2.replace(HWC_Code, patchHwc)
			else:
				patchedFsys3 = patchedFsys2

			if hwcOffset != -1:
				patchedFsys4 = patchedFsys3.replace(hwcCode, patchHwc)
			else:
				patchedFsys4 = patchedFsys3

			# If patchedFsys4 exists then proceed with CRC32 calculation
			try:
				patchedFsys4
			except NameError:
				print(colored('Error: Patch Variable Unassigned', 'red'))
			else:
				patchedCrc = '{:02x}'.format(binascii.crc32(patchedFsys4) & 0xffffffff)
				patchedCrcReversed = ("".join(reversed([patchedCrc[i:i+2] for i in range(0, len(patchedCrc), 2)])))
				patchedCrcReversedBytes = bytes.fromhex(patchedCrcReversed)

			writeFsys = True
		else:
			print(colored('Fsys Not Patched: Serial Length Incorrect', 'red'))

	# Write Pached EFI File
	# If Output File Option Activated
	try:
		outputfile
	except NameError:
		print(colored('Patching Failed: Output File Option Not Set', 'red'))
	else:
		# If Variable Containing Original EFI Exists - is Required to Create Base of Patched EFI
		try:
			entire_efi
		except NameError:
			print(colored('Patching Failed: Missing Variable Containing EFI Data', 'red'))
		else:
			try:
				with open(outputfile, 'wb+') as write_file:
					write_file.write(entire_efi)

					# Write ME Patch
					# If ME File to Insert Exists
					try:
						patchRegion
					except NameError:
						print('ME Region Patch Variable Unassigned - Skipping')
					else:
						# Check Which ME Header Version was Found and Insert New Region
						if meRegionOffsetV1 != -1:
							print('Patching ME Region')
							write_file.seek(meRegionOffsetV1)
							write_file.write(patchRegion)
						elif meRegionOffsetV2 != -1:
							print('Patching ME Region')
							write_file.seek(meRegionOffsetV2)
							write_file.write(patchRegion)
						elif meRegionOffsetV3 != -1:
							print('Patching ME Region')
							write_file.seek(meRegionOffsetV3)
							write_file.write(patchRegion)
						else:
							print(colored('Error: Unable to Locate ME Region Offset', 'red'))
					
					# Write NVRAM Patch	
					if clearNvram == True:
						if nvramStartOffset != -1 and nvramEndOffset != -1:
							print('Clearing NVRAM')
							#Calculate NVRam Fill Bytes
							nvramFill = b'\xFF' * (nvramEndOffset - (nvramStartOffset + 16))
							write_file.seek(nvramStartOffset + 16)
							write_file.write(nvramFill)
						else:
							print(colored('Error: Unable to Locate NVRAM Offsets', 'red'))

					# Write Fsys Patch
					if writeFsys == True:
						if fsysStartOffset != -1:
							print('Patching Fsys: Serial & HWC')
							print('Patch Serial: ', colored(patchSerial.decode('utf-8'), 'yellow'))
							print('Patch HWC: ', colored(patchHwc.decode('utf-8'), 'yellow'))
							#Look up Identifier Associated with Patched Serial & HWC
							patchedModel, searchPatchMessage = search_and_update_db(database, patchHwc.decode("utf-8"), database)
							print('Patch Identifier: ', colored(patchedModel, 'yellow'))
							print(searchPatchMessage)
							write_file.seek(fsysStartOffset)
							write_file.write(patchedFsys4)
						else:
							print(colored('Error: Unable to Locate Fsys Offsets', 'red'))

					# Write CRC32 Patch
					if writeFsys == True:
						if crc32Offset != -1:
							print('Patching CRC32')
							print('Patch CRC32: ', colored(patchedCrc.upper(), 'yellow'))
							write_file.seek(crc32Offset)
							write_file.write(patchedCrcReversedBytes)
						else:
							print(colored('Error: Unable to Locate CRC32 Offset', 'red'))

					# Write Firmware Lock Patch
					if removeFirmwareLock == True:
						if lockStartOffset != -1 and lockEndOffset != -1:
							print('Removing Firmware Lock')
							# Calculate Lock Fill Bytes
							lockFill = b'\xFF' * (lockEndOffset - (lockStartOffset + 16))
							write_file.seek(lockStartOffset + 16)
							write_file.write(lockFill)
						else:
							print(colored('Error: Unable to Locate Firmware Lock Offsets', 'red'))

					print(colored('Patching Complete', 'green'))

			except FileNotFoundError:
				print(colored('Unable to Create Output File', 'red'))

if __name__ == "__main__":
	main(sys.argv[1:])