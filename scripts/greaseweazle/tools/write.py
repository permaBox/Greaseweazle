# greaseweazle/tools/write.py
#
# Greaseweazle control script: Write Image to Disk.
#
# Written & released by Keir Fraser <keir.xen@gmail.com>
#
# This is free and unencumbered software released into the public domain.
# See the file COPYING for more details, or visit <http://unlicense.org>.

description = "Write a disk from the specified image file."

import sys

from greaseweazle.tools import util
from greaseweazle import usb as USB


# Read and parse the image file.
def open_image(args):
    image_class = util.get_image_class(args.file)
    if hasattr(image_class, 'from_filename'):
        image = image_class.from_filename(args.file)
    else:
        with open(args.file, "rb") as f:
            image = image_class.from_file(f.read())
    return image


# write_from_image:
# Writes the specified image file to floppy disk.
def write_from_image(usb, args, image):

    # @drive_ticks is the time in Greaseweazle ticks between index pulses.
    # We will adjust the flux intervals per track to allow for this.
    flux = usb.read_track(2)
    drive_ticks = (flux.index_list[0] + flux.index_list[1]) / 2
    del flux

    for cyl in range(args.scyl, args.ecyl+1):
        for side in range(0, args.nr_sides):

            print("\rWriting Track %u.%u..." % (cyl, side), end="")
            usb.seek((cyl, cyl*2)[args.double_step], side)

            track = image.get_track(cyl, side, writeout=True)
            if not track:
                if args.erase_empty:
                    usb.erase_track(drive_ticks * 1.1)
                continue

            flux = track.flux_for_writeout()
            
            # @factor adjusts flux times for speed variations between the
            # read-in and write-out drives.
            factor = drive_ticks / flux.index_list[0]

            # Convert the flux samples to Greaseweazle sample frequency.
            rem = 0.0
            flux_list = []
            for x in flux.list:
                y = x * factor + rem
                val = int(round(y))
                rem = y - val
                flux_list.append(val)

            # Encode the flux times for Greaseweazle, and write them out.
            usb.write_track(flux_list, flux.terminate_at_index)

    print()


def main(argv):

    parser = util.ArgumentParser()
    parser.add_argument("--drive", type=util.drive_letter, default='A',
                        help="drive to write (A,B,0,1,2)")
    parser.add_argument("--scyl", type=int, default=0,
                        help="first cylinder to write")
    parser.add_argument("--ecyl", type=int, default=81,
                        help="last cylinder to write")
    parser.add_argument("--single-sided", action="store_true",
                        help="single-sided write")
    parser.add_argument("--double-step", action="store_true",
                        help="double-step drive heads")
    parser.add_argument("--erase-empty", action="store_true",
                        help="erase empty tracks (default: skip)")
    parser.add_argument("file", help="input filename")
    parser.add_argument("device", nargs="?", help="serial device")
    parser.description = description
    parser.prog += ' ' + argv[1]
    args = parser.parse_args(argv[2:])
    args.nr_sides = 1 if args.single_sided else 2

    try:
        usb = util.usb_open(args.device)
        image = open_image(args)
        util.with_drive_selected(write_from_image, usb, args, image)
    except USB.CmdError as error:
        print("Command Failed: %s" % error)


if __name__ == "__main__":
    main(sys.argv)

# Local variables:
# python-indent: 4
# End:
