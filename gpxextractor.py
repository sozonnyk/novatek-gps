#!/usr/bin/env python
#
# Author: Sergei Franco (sergei at sergei.nz)
# License: GPL3
# Warranty: NONE! Use at your own risk!
# Disclaimer: I am no programmer!
# Description: this script will crudely extract embedded GPS data from Novatek generated MP4 files.
#

import os, struct, sys, re

class GpxExtractor:

	def __init__(self):
		self.mp4 = re.compile(r'\.[mM][pP]4$')

	def find_files(self, base):
		matches = []
		for root, dirnames, filenames in os.walk(base):
			for filename in list(filter(lambda x: self.mp4.search(x), filenames)):
				matches.append(os.path.join(root, filename))
		return matches

	def fix_time(self, hour, minute, second, year, month, day):
		return "%d-%02d-%02dT%02d:%02d:%02dZ" % ((year + 2000), int(month), int(day), int(hour), int(minute), int(second))


	def fix_coordinates(self, hemisphere, coordinate):
		# Novatek stores coordinates in odd DDDmm.mmmm format
		minutes = coordinate % 100.0
		degrees = coordinate - minutes
		coordinate = degrees / 100.0 + (minutes / 60.0)
		if hemisphere == 'S' or hemisphere == 'W':
			return -1 * float(coordinate)
		else:
			return float(coordinate)


	def fix_speed(self, speed):
		# 1 knot = 0.514444 m/s
		return speed * float(0.514444)


	def get_atom_info(self, eight_bytes):
		try:
			atom_size, atom_type = struct.unpack('>I4s', eight_bytes)
		except struct.error:
			return 0, ''
		return int(atom_size), atom_type.decode()


	def get_gps_atom_info(self, eight_bytes):
		atom_pos, atom_size = struct.unpack('>II', eight_bytes)
		return int(atom_pos), int(atom_size)


	def get_gps_atom(self, gps_atom_info, f):
		atom_pos, atom_size = gps_atom_info
		f.seek(atom_pos)
		data = f.read(atom_size)
		expected_type = 'free'
		expected_magic = 'GPS '
		atom_size1, atom_type, magic = struct.unpack_from('>I4s4s', data)
		atom_type = atom_type.decode()
		magic = magic.decode()
		# sanity:
		if atom_size != atom_size1 or atom_type != expected_type or magic != expected_magic:
			print(
			"Error! skipping atom at %x (expected size:%d, actual size:%d, expected type:%s, actual type:%s, expected magic:%s, actual maigc:%s)!" % (
			int(atom_pos), atom_size, atom_size1, expected_type, atom_type, expected_magic, magic))
			return

		hour, minute, second, year, month, day, active, latitude_b, longitude_b, unknown2, latitude, longitude, speed = struct.unpack_from(
			'<IIIIIIssssfff', data, 48)
		active = active.decode()
		latitude_b = latitude_b.decode()
		longitude_b = longitude_b.decode()

		time = self.fix_time(hour, minute, second, year, month, day)
		latitude = self.fix_coordinates(latitude_b, latitude)
		longitude = self.fix_coordinates(longitude_b, longitude)
		speed = self.fix_speed(speed)

		# it seems that A indicate reception
		if active != 'A':
			#print("Skipping: lost GPS satelite reception. Time: %s." % time)
			return

		return (latitude, longitude, time, speed)


	def get_gpx(self, gps_data, out_file):
		gpx = '<?xml version="1.0" encoding="UTF-8"?>\n'
		gpx += '<gpx version="1.0"\n'
		gpx += '\tcreator="Sergei\'s Novatek MP4 GPS parser"\n'
		gpx += '\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
		gpx += '\txmlns="http://www.topografix.com/GPX/1/0"\n'
		gpx += '\txsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">\n'
		gpx += "\t<name>%s</name>\n" % out_file
		gpx += '\t<url>sergei.nz</url>\n'
		gpx += "\t<trk><name>%s</name><trkseg>\n" % out_file
		for l in gps_data:
			if l:
				gpx += "\t\t<trkpt lat=\"%f\" lon=\"%f\"><time>%s</time><speed>%f</speed></trkpt>\n" % l
		gpx += '\t</trkseg></trk>\n'
		gpx += '</gpx>\n'
		return gpx


	def process_file(self, in_file):
		gps_data = []
		#print("Reading %s" % in_file)
		with open(in_file, "rb") as f:
			offset = 0
			while True:
				atom_pos = f.tell()
				atom_size, atom_type = self.get_atom_info(f.read(8))
				if atom_size == 0:
					break

				if atom_type == 'moov':
					#print("Found moov atom...")
					sub_offset = offset + 8

					while sub_offset < (offset + atom_size):
						sub_atom_pos = f.tell()
						sub_atom_size, sub_atom_type = self.get_atom_info(f.read(8))

						if str(sub_atom_type) == 'gps ':
							#print("Found gps chunk descriptor atom...")
							gps_offset = 16 + sub_offset  # +16 = skip headers
							f.seek(gps_offset, 0)
							while gps_offset < (sub_offset + sub_atom_size):
								gps_data.append(self.get_gps_atom(self.get_gps_atom_info(f.read(8)), f))
								gps_offset += 8
								f.seek(gps_offset, 0)

						sub_offset += sub_atom_size
						f.seek(sub_offset, 0)

				offset += atom_size
				f.seek(offset, 0)

		out_file = re.sub(self.mp4, '.gpx', in_file)
		gpx = self.get_gpx(gps_data, out_file)

		if gpx:
			with open(out_file, "w") as f:
				print("Wiriting %s" % out_file)
				f.write(gpx)
	
	def process(self, base):
		for f in self.find_files(base):
			self.process_file(f)	
	
def main():
	dir = sys.argv[1] if len(sys.argv) > 1 else '.'
	extractor = GpxExtractor().process(dir)

if __name__ == "__main__":
    main()
