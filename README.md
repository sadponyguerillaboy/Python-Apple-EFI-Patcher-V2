# Python-Apple-EFI-Patcher-V2
Version 2 of the Apple EFI Patcher written in Python. During the development of the Swift Apple EFI Patcher, a new and improved search methodolog for locating offsets was developed. This methodolgy was reimplimented back into a python based version of the patcher.

`patcher.py` is a python3 script designed to automate the patching process of Apple EFI Rom dumps. The script can change the serial number, which will also automatically change the hwc field, and correct the CRC32 for the Fsys block. The script also has the ability to clear NVRAM, remove firmware locks and to Clean ME Regions.

# Usage:
Place patcher.py, database.json and the ME_Regions folder into the same directory. Run as follows:

```
python3 patcher.py -i <input filename> -o <output filename> -s <serial to insert> -m <me region file> -n -l
```

__example:__ 
```
python3 patcher.py -i firmware.bin -o dump.bin -s ABCDEFGH1234 -m ME_Regions/MBA61/10.13.6_MBA61_0107_B00.rgn -n -l
```

__Note:__ You can drag and drop files into the terminal to avoid having to type locations.

__Options:__
```
-i <input filename>     -- name of the file to be modified
-o <output filename>    -- name of the newly modified file
-s <serial to insert>   -- serial number to be inserted
-m <me region file>     -- name of the me region file to insert
-n                      -- clear NVRAM
-l                      -- remove firmware lock
```

__Improvements in Version 2:__
```
- code rewritten from scratch - massive optimizations and improvements
- implimentation of new search based offset acquisition
- clearing of NVRAM support added
- proper preservation of NVRAM and Firmware Lock Section Headers
- proper masking of crc32 values
- extensive error handling implemented
```

__Note:__ 

ME Regions have been extracted from macOS 10.12.6, 10.13.6, 10.14.6 and 10.15.b8. They are contained in the ME_Regions folder. Each subfolder corresponds to a system type. (example: MBA61 = MacBook Air 6,1). Each ME region file is named in accordance to the macOS version from which it was extracted, the system type, the Boot Rom Version and the ME Version. (example: 10.13.6_MBA61_0107_B00_9.5.3.1526.rgn, means that the ME Region was extracted from macOS High Sierra 10.13.6, it is for a MacBook Air 6,1, it came from an EFI with Boot Rom Version 0107_B00 and the ME Version is 9.5.3.1526). In some instances, regions between macOS versions may be identical. It seemed that anything extracted from .scap files rather an .fd files were the same between OS versions. You can use something like <a href="https://ridiculousfish.com/hexfiend/">hex fiend</a> to compare and see if they are identical, or <a href="https://github.com/platomav/MEAnalyzer">ME Analyzer</a> to find out the ME Version. Also, anything extracted from macOS 10.14.6 onward has no references to Boot Rom Versions in their names. Not that it particularly matters, what you want to match up is the ME version number.
